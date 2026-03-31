"""Quick test of the new pipeline (no normalizer, raw -> structured)."""
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
    cursor = db.jobs.find(
        {"_id": {"$regex": "^remoteok_test_v2_"}},
        {"title": 1, "company": 1, "category": 1, "seniority_level": 1,
         "is_remote": 1, "work_arrangement": 1, "quality_score": 1,
         "tags": 1, "skills": 1, "salary_period": 1, "company_logo": 1},
    )
    rows = await cursor.to_list(length=3)
    print(f"  Read back {len(rows)} jobs from DB:")
    for r in rows:
        print(f"    {r['_id']}: title={r.get('title')}, category={r.get('category')}, "
              f"seniority={r.get('seniority_level')}, remote={r.get('is_remote')}, "
              f"work={r.get('work_arrangement')}, quality={r.get('quality_score')}, "
              f"tags={r.get('tags')}")

    # Clean up test data
    result = await db.jobs.delete_many({"_id": {"$regex": "^remoteok_test_v2_"}})
    print(f"  Cleaned up {result.deleted_count} test documents")

    await db.disconnect()
    print("\nAll tests passed.")


asyncio.run(test())
