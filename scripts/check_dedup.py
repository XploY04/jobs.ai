"""Check deduplication status in the database."""
import asyncio
import sys
sys.path.insert(0, '.')
from src.database.operations import db


async def check():
    await db.connect()

    # Total jobs
    total = await db.jobs.count_documents({})
    print(f"Total jobs in DB: {total:,}")

    # Jobs per source
    pipeline = [
        {"$group": {"_id": "$source", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    print("\nJobs per source:")
    async for doc in db.jobs.aggregate(pipeline):
        print(f"  {doc['_id']:20s}: {doc['count']:,}")

    # Check for duplicate title_company_hash (same hash, multiple rows)
    dup_pipeline = [
        {"$match": {"title_company_hash": {"$ne": None}}},
        {"$group": {"_id": "$title_company_hash", "cnt": {"$sum": 1}}},
        {"$match": {"cnt": {"$gt": 1}}},
        {"$sort": {"cnt": -1}},
    ]
    dups = await db.jobs.aggregate(dup_pipeline).to_list(length=None)
    dup_job_count = sum(d["cnt"] for d in dups)
    print(f"\nDuplicate title+company hashes: {len(dups)} groups ({dup_job_count} total rows)")

    if dups:
        print("\nSample duplicates (first 15):")
        for d in dups[:15]:
            h = d["_id"]
            rows = await db.jobs.find(
                {"title_company_hash": h},
                {"_id": 1, "title": 1, "company": 1, "source": 1},
            ).to_list(length=None)
            print(f"\n  Hash {h}: {d['cnt']} copies")
            for r in rows:
                print(f"    [{r['source']:15s}] {r['title'][:60]:60s} @ {r['company']}")

    # Check null hashes
    null_hash = await db.jobs.count_documents({"title_company_hash": None})
    print(f"\nJobs with NULL title_company_hash: {null_hash}")

    # Cross-source overlap
    cross_pipeline = [
        {"$match": {"title_company_hash": {"$ne": None}}},
        {"$group": {
            "_id": "$title_company_hash",
            "sources": {"$addToSet": "$source"},
            "total": {"$sum": 1},
            "sample_title": {"$first": "$title"},
            "sample_company": {"$first": "$company"},
        }},
        {"$match": {"sources.1": {"$exists": True}}},
        {"$sort": {"total": -1}},
        {"$limit": 15},
    ]
    cross_rows = await db.jobs.aggregate(cross_pipeline).to_list(length=None)
    print(f"\nCross-source duplicates (same job, different sources): {len(cross_rows)} groups")
    for row in cross_rows:
        print(f"\n  [{len(row['sources'])} sources, {row['total']} rows] {row['sample_title'][:60]} @ {row['sample_company']}")
        for src in row["sources"]:
            print(f"    - {src}")

    await db.disconnect()


asyncio.run(check())
