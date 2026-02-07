"""Quick test of the new pipeline (no normalizer, raw → structured)."""
import sys, asyncio, json
sys.path.insert(0, '.')

from src.agents.remoteok import RemoteOKFetcher
from src.enrichment.enrichment_pipeline import EnrichmentPipeline
from src.database.operations import db


async def test():
    # Test with AI DISABLED (fallback path)
    pipeline = EnrichmentPipeline(use_ai=False)
    fetcher = RemoteOKFetcher()
    raw = await fetcher.fetch_jobs()
    print(f"1. Fetched: {len(raw)} raw jobs")

    # New single-step: raw -> processed (no normalize step)
    processed = await pipeline.process_source("remoteok", raw)
    print(f"2. Processed: {len(processed)} jobs")

    if processed:
        sample = processed[0]
        print(f"\nFinal fields ({len(sample.keys())} total):")
        for key in sorted(sample.keys()):
            val = sample[key]
            if isinstance(val, str) and len(val) > 80:
                val = val[:80] + "..."
            elif isinstance(val, dict):
                val = json.dumps(val, default=str)[:80]
            elif isinstance(val, list) and len(val) > 5:
                val = str(val[:5]) + "..."
            print(f"  {key}: {val}")

    # Test DB save
    print("\n--- Testing DB save ---")
    await db.connect()
    
    # Use just 3 jobs to test
    test_jobs = processed[:3]
    # Give them unique IDs to avoid dedup
    for i, job in enumerate(test_jobs):
        job["source_id"] = f"test_v2_{i}"
        job["id"] = f"remoteok_test_v2_{i}"
        job["title_company_hash"] = f"test_v2_hash_{i}"
    
    stats = await db.save_jobs(test_jobs)
    print(f"  DB save result: {stats}")
    
    # Read back and verify
    from sqlalchemy import text
    async with db.session_maker() as sess:
        result = await sess.execute(text(
            "SELECT id, title, company, category, seniority_level, is_remote, "
            "work_arrangement, quality_score, tags, skills, salary_period, company_logo "
            "FROM jobs WHERE id LIKE 'remoteok_test_v2_%' LIMIT 3"
        ))
        rows = result.fetchall()
        print(f"  Read back {len(rows)} jobs from DB:")
        for row in rows:
            print(f"    {row[0]}: title={row[1]}, category={row[3]}, seniority={row[4]}, "
                  f"remote={row[5]}, work={row[6]}, quality={row[7]}, tags={row[8]}")
    
    # Clean up test data
    async with db.session_maker() as sess:
        await sess.execute(text("DELETE FROM jobs WHERE id LIKE 'remoteok_test_v2_%'"))
        await sess.commit()
        print("  Cleaned up test data")
    
    await db.disconnect()
    print("\nAll tests passed.")


asyncio.run(test())
