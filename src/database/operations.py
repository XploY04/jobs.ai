import hashlib
import ssl
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func, or_, Boolean, text
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
                    job_id = job_data.get('id') or f"{job_data['source']}_{job_data['source_id']}"
                    title_company_hash = job_data.get('title_company_hash') or self._hash_title_company(
                        job_data.get('title', ''), job_data.get('company', '')
                    )

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

                    job = Job(
                        # ── Identity ──
                        id=job_id,
                        source=job_data.get('source', ''),
                        source_id=str(job_data.get('source_id', '')),
                        source_url=job_data.get('source_url'),
                        # ── Core Job Info ──
                        title=job_data.get('title', ''),
                        company=job_data.get('company', 'Unknown'),
                        company_logo=job_data.get('company_logo'),
                        company_website=job_data.get('company_website'),
                        description=job_data.get('description', ''),
                        short_description=job_data.get('short_description'),
                        # ── Location ──
                        location=job_data.get('location'),
                        country=job_data.get('country'),
                        city=job_data.get('city'),
                        state=job_data.get('state'),
                        is_remote=job_data.get('is_remote'),
                        work_arrangement=job_data.get('work_arrangement'),
                        latitude=job_data.get('latitude'),
                        longitude=job_data.get('longitude'),
                        # ── Employment Details ──
                        employment_type=job_data.get('employment_type'),
                        seniority_level=job_data.get('seniority_level'),
                        department=job_data.get('department'),
                        category=job_data.get('category'),
                        # ── Compensation ──
                        salary_min=self._to_str(job_data.get('salary_min')),
                        salary_max=self._to_str(job_data.get('salary_max')),
                        salary_currency=job_data.get('salary_currency'),
                        salary_period=job_data.get('salary_period'),
                        # ── Skills & Requirements ──
                        skills=job_data.get('skills'),
                        required_experience_years=job_data.get('required_experience_years'),
                        required_education=job_data.get('required_education'),
                        key_responsibilities=job_data.get('key_responsibilities'),
                        nice_to_have_skills=job_data.get('nice_to_have_skills'),
                        # ── Benefits & Perks ──
                        benefits=job_data.get('benefits'),
                        visa_sponsorship=job_data.get('visa_sponsorship'),
                        # ── Dates ──
                        posted_at=job_data.get('posted_at'),
                        application_deadline=job_data.get('application_deadline'),
                        # ── Apply ──
                        apply_url=job_data.get('apply_url', ''),
                        apply_options=job_data.get('apply_options'),
                        # ── Quality / Meta ──
                        tags=job_data.get('tags'),
                        quality_score=job_data.get('quality_score'),
                        raw_data=job_data.get('raw_data'),
                        title_company_hash=title_company_hash,
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

    @staticmethod
    def _build_tsquery(search: str) -> str:
        """Convert user search string into a PostgreSQL tsquery.

        - Splits on whitespace
        - Strips non-alphanumeric chars
        - Joins with '&' (AND) so all terms must match
        - Appends ':*' for prefix matching ("pyth" matches "python")
        """
        import re
        words = re.findall(r'[\w]+', search.strip())
        if not words:
            return ''
        return ' & '.join(f"{w}:*" for w in words)

    async def count_jobs(
        self,
        *,
        search: Optional[str] = None,
        sources: Optional[List[str]] = None,
        employment_type: Optional[str] = None,
        remote_only: bool = False,
        seniority: Optional[List[str]] = None,
        category: Optional[List[str]] = None,
    ) -> int:
        """Count total jobs matching the filters."""

        if not self.session_maker:
            raise RuntimeError("Database session maker not initialized")

        stmt = select(func.count(Job.id))

        if search:
            tsquery = self._build_tsquery(search)
            stmt = stmt.where(Job.search_vector.op('@@')(func.to_tsquery('english', tsquery)))

        if sources:
            stmt = stmt.where(Job.source.in_(sources))

        if employment_type:
            stmt = stmt.where(func.lower(Job.employment_type) == employment_type.lower())

        if remote_only:
            stmt = stmt.where(Job.is_remote == True)

        if seniority:
            seniority_lower = [s.lower() for s in seniority]
            stmt = stmt.where(func.lower(Job.seniority_level).in_(seniority_lower))

        if category:
            category_lower = [c.lower() for c in category]
            stmt = stmt.where(func.lower(Job.category).in_(category_lower))

        async with self.session_maker() as session:
            result = await session.execute(stmt)
            return result.scalar() or 0

    async def list_jobs(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
        sources: Optional[List[str]] = None,
        employment_type: Optional[str] = None,
        remote_only: bool = False,
        seniority: Optional[List[str]] = None,
        category: Optional[List[str]] = None,
    ) -> List[Job]:
        """Return paginated jobs with lightweight filtering."""

        if not self.session_maker:
            raise RuntimeError("Database session maker not initialized")

        limit = max(1, min(limit, 200))
        offset = max(0, offset)

        if search:
            tsquery = self._build_tsquery(search)
            ts_expr = func.to_tsquery('english', tsquery)
            rank = func.ts_rank_cd(Job.search_vector, ts_expr)
            stmt = select(Job).where(
                Job.search_vector.op('@@')(ts_expr)
            ).order_by(rank.desc(), Job.posted_at.desc())
        else:
            stmt = select(Job).order_by(Job.posted_at.desc())

        if sources:
            stmt = stmt.where(Job.source.in_(sources))

        if employment_type:
            stmt = stmt.where(func.lower(Job.employment_type) == employment_type.lower())

        if remote_only:
            stmt = stmt.where(Job.is_remote == True)

        if seniority:
            seniority_lower = [s.lower() for s in seniority]
            stmt = stmt.where(func.lower(Job.seniority_level).in_(seniority_lower))

        if category:
            category_lower = [c.lower() for c in category]
            stmt = stmt.where(func.lower(Job.category).in_(category_lower))

        stmt = stmt.offset(offset).limit(limit)

        async with self.session_maker() as session:
            result = await session.execute(stmt)
            jobs = result.scalars().all()

        return jobs

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Fetch a single job by identifier."""

        if not self.session_maker:
            raise RuntimeError("Database session maker not initialized")

        async with self.session_maker() as session:
            return await session.get(Job, job_id)

    async def get_filter_options(self) -> Dict[str, Any]:
        """Get available filter options with job counts."""

        if not self.session_maker:
            raise RuntimeError("Database session maker not initialized")

        async with self.session_maker() as session:
            # Get seniority options
            seniority_result = await session.execute(
                select(Job.seniority_level, func.count(Job.id))
                .where(Job.seniority_level.isnot(None))
                .group_by(Job.seniority_level)
                .order_by(func.count(Job.id).desc())
            )
            seniority = [
                {"value": row[0], "count": row[1]} 
                for row in seniority_result.all()
            ]

            # Get category options
            category_result = await session.execute(
                select(Job.category, func.count(Job.id))
                .where(Job.category.isnot(None))
                .group_by(Job.category)
                .order_by(func.count(Job.id).desc())
            )
            categories = [
                {"value": row[0], "count": row[1]} 
                for row in category_result.all()
            ]

            # Get source options
            source_result = await session.execute(
                select(Job.source, func.count(Job.id))
                .group_by(Job.source)
                .order_by(func.count(Job.id).desc())
            )
            sources = [
                {"value": row[0], "count": row[1]} 
                for row in source_result.all()
            ]

            # Count remote jobs
            remote_result = await session.execute(
                select(func.count(Job.id))
                .where(Job.is_remote == True)
            )
            remote_count = remote_result.scalar() or 0

            return {
                "seniority": seniority,
                "category": categories,
                "sources": sources,
                "remote_count": remote_count,
            }


db = Database()
