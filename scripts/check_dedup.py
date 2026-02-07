"""Check deduplication status in the database."""
import asyncio
import sys
sys.path.insert(0, '.')
from src.database.operations import db
from src.database.models import Job
from sqlalchemy import select, func, text


async def check():
    await db.connect()
    async with db.session_maker() as session:
        # Total jobs
        total = (await session.execute(select(func.count(Job.id)))).scalar()
        print(f"Total jobs in DB: {total:,}")

        # Jobs per source
        stmt = select(Job.source, func.count(Job.id)).group_by(Job.source).order_by(func.count(Job.id).desc())
        result = await session.execute(stmt)
        print("\nJobs per source:")
        for source, count in result:
            print(f"  {source:20s}: {count:,}")

        # Check for duplicate title_company_hash (same hash, multiple rows)
        dup_stmt = (
            select(Job.title_company_hash, func.count(Job.id).label("cnt"))
            .where(Job.title_company_hash.isnot(None))
            .group_by(Job.title_company_hash)
            .having(func.count(Job.id) > 1)
        )
        dups = (await session.execute(dup_stmt)).all()
        dup_job_count = sum(cnt for _, cnt in dups)
        print(f"\nDuplicate title+company hashes: {len(dups)} groups ({dup_job_count} total rows)")

        if dups:
            print("\nSample duplicates (first 15):")
            for h, cnt in dups[:15]:
                detail = await session.execute(
                    select(Job.id, Job.title, Job.company, Job.source).where(Job.title_company_hash == h)
                )
                rows = detail.all()
                print(f"\n  Hash {h}: {cnt} copies")
                for r in rows:
                    print(f"    [{r.source:15s}] {r.title[:60]:60s} @ {r.company}")

        # Check null hashes
        null_hash = (await session.execute(
            select(func.count(Job.id)).where(Job.title_company_hash.is_(None))
        )).scalar()
        print(f"\nJobs with NULL title_company_hash: {null_hash}")

        # Cross-source overlap
        cross_src = await session.execute(text("""
            SELECT title_company_hash, COUNT(DISTINCT source) as src_count, COUNT(*) as total
            FROM jobs
            WHERE title_company_hash IS NOT NULL
            GROUP BY title_company_hash
            HAVING COUNT(DISTINCT source) > 1
            ORDER BY total DESC
            LIMIT 15
        """))
        cross_rows = cross_src.all()
        print(f"\nCross-source duplicates (same job, different sources): {len(cross_rows)} groups")
        for h, sc, tc in cross_rows:
            detail2 = await session.execute(
                select(Job.source, Job.title, Job.company).where(Job.title_company_hash == h)
            )
            rr = detail2.all()
            print(f"\n  [{sc} sources, {tc} rows] {rr[0].title[:60]} @ {rr[0].company}")
            for r in rr:
                print(f"    - {r.source}")

    await db.disconnect()


asyncio.run(check())
