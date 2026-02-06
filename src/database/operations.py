import hashlib
import ssl
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine.url import make_url

from src.database.models import Base, Job
from src.utils.config import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class Database:
    """Database helper for connections and CRUD operations."""

    def __init__(self) -> None:
        self.engine = None
        self.session_maker: sessionmaker[AsyncSession] | None = None

    async def connect(self) -> None:
        """Initialize database connection and ensure tables exist."""

        connect_args = {}
        raw_url = settings.database_url
        url = make_url(raw_url)

        driver = url.drivername
        if driver in {"postgres", "postgresql"}:
            driver = "postgresql+asyncpg"

        query = dict(url.query)
        sslmode = query.pop("sslmode", None)
        sslrootcert = query.pop("sslrootcert", None)
        ssl_no_verify = query.pop("ssl_no_verify", None)

        if sslmode:
            sslmode = sslmode.lower()

        if ssl_no_verify:
            ssl_no_verify = ssl_no_verify.lower() in {"1", "true", "yes"}

        if sslmode == "disable":
            connect_args["ssl"] = False
        elif sslmode in {"require", "verify-ca", "verify-full"}:
            if ssl_no_verify:
                context = ssl._create_unverified_context()
            else:
                context = ssl.create_default_context(cafile=sslrootcert) if sslrootcert else ssl.create_default_context()
                context.check_hostname = sslmode == "verify-full"
            connect_args["ssl"] = context

        async_url = url.set(drivername=driver, query=query)
        self.engine = create_async_engine(
            async_url.render_as_string(hide_password=False),
            echo=False,
            connect_args=connect_args,
        )
        self.session_maker = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database connected and tables ensured")

    async def disconnect(self) -> None:
        """Cleanly close database connections."""

        if self.engine:
            await self.engine.dispose()
            logger.info("Database disconnected")

    async def save_jobs(self, jobs: List[Dict[str, Any]]) -> Dict[str, int]:
        """Insert jobs while skipping duplicates."""

        stats = {"new": 0, "skipped": 0}

        if not self.session_maker:
            raise RuntimeError("Database session maker not initialized")

        async with self.session_maker() as session:
            for job_data in jobs:
                try:
                    job_id = f"{job_data['source']}_{job_data['source_id']}"
                    title_company_hash = self._hash_title_company(job_data['title'], job_data['company'])

                    exists = await session.get(Job, job_id)
                    if exists:
                        stats["skipped"] += 1
                        continue

                    # Check for duplicate title + company
                    duplicate_stmt = select(Job.id).where(Job.title_company_hash == title_company_hash)
                    duplicate = await session.execute(duplicate_stmt)
                    if duplicate.scalar():
                        stats["skipped"] += 1
                        continue

                    salary_min = self._to_str(job_data.get('salary_min'))
                    salary_max = self._to_str(job_data.get('salary_max'))

                    job = Job(
                        id=job_id,
                        source=job_data['source'],
                        source_id=job_data['source_id'],
                        title=job_data['title'],
                        company=job_data['company'],
                        description=job_data['description'],
                        location=job_data['location'],
                        employment_type=job_data.get('employment_type'),
                        salary_min=salary_min,
                        salary_max=salary_max,
                        salary_currency=job_data.get('salary_currency'),
                        apply_url=job_data['apply_url'],
                        posted_at=job_data['posted_at'],
                        title_company_hash=title_company_hash,
                        raw_data=job_data.get('raw_data'),
                    )

                    session.add(job)
                    stats["new"] += 1

                except Exception as exc:  # pylint: disable=broad-except
                    logger.error("Error saving job: %s", exc, exc_info=True)
                    await session.rollback()
                    stats["skipped"] += 1

            await session.commit()

        return stats

    @staticmethod
    def _hash_title_company(title: str, company: str) -> str:
        text = f"{title.lower().strip()}_{company.lower().strip()}"
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    @staticmethod
    def _to_str(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return str(value)

    async def list_jobs(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
        sources: Optional[List[str]] = None,
        employment_type: Optional[str] = None,
        remote_only: bool = False,
    ) -> List[Job]:
        """Return paginated jobs with lightweight filtering."""

        if not self.session_maker:
            raise RuntimeError("Database session maker not initialized")

        limit = max(1, min(limit, 200))
        offset = max(0, offset)

        stmt = select(Job).order_by(Job.posted_at.desc()).offset(offset).limit(limit)

        if search:
            pattern = f"%{search.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Job.title).like(pattern),
                    func.lower(Job.description).like(pattern),
                    func.lower(Job.company).like(pattern),
                )
            )

        if sources:
            stmt = stmt.where(Job.source.in_(sources))

        if employment_type:
            stmt = stmt.where(func.lower(Job.employment_type) == employment_type.lower())

        async with self.session_maker() as session:
            result = await session.execute(stmt)
            jobs = result.scalars().all()

        if remote_only:
            jobs = [job for job in jobs if (job.location or {}).get("remote")]

        return jobs

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Fetch a single job by identifier."""

        if not self.session_maker:
            raise RuntimeError("Database session maker not initialized")

        async with self.session_maker() as session:
            return await session.get(Job, job_id)


db = Database()
