#!/usr/bin/env python
"""
Data validation and quality checks for the jobs database.

Usage:
    python scripts/validate_data.py
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone

# Add src to path
sys.path.insert(0, '/app' if sys.platform == 'linux' else '.')

from src.database.operations import db


async def validate_data():
    """Run comprehensive data validation checks"""

    print("=" * 60)
    print("JOB DATABASE VALIDATION REPORT")
    print("=" * 60)
    print(f"Generated: {datetime.now(timezone.utc).isoformat()}\n")

    await db.connect()

    try:
        # 1. Total jobs count
        total_jobs = await db.jobs.count_documents({})
        print(f"Total Jobs: {total_jobs:,}")

        if total_jobs == 0:
            print("\nWARNING: No jobs found in database!")
            return

        # 2. Jobs per source
        print("\n" + "=" * 60)
        print("JOBS BY SOURCE")
        print("=" * 60)

        pipeline = [
            {"$group": {"_id": "$source", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]
        async for doc in db.jobs.aggregate(pipeline):
            percentage = (doc["count"] / total_jobs) * 100
            print(f"  {doc['_id']:12s}: {doc['count']:5,} ({percentage:5.1f}%)")

        # 3. Recent jobs (last 7 days)
        print("\n" + "=" * 60)
        print("RECENT JOBS (Last 7 Days)")
        print("=" * 60)

        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_count = await db.jobs.count_documents({"posted_at": {"$gte": seven_days_ago}})
        recent_percentage = (recent_count / total_jobs) * 100
        print(f"  Recent: {recent_count:,} ({recent_percentage:.1f}% of total)")

        # 4. Check for duplicates
        print("\n" + "=" * 60)
        print("DUPLICATE ANALYSIS")
        print("=" * 60)

        dup_pipeline = [
            {"$group": {"_id": "$title_company_hash", "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 1}}},
        ]
        duplicates = await db.jobs.aggregate(dup_pipeline).to_list(length=None)

        if duplicates:
            total_dup_jobs = sum(d["count"] - 1 for d in duplicates)
            print(f"  Found {len(duplicates)} duplicate groups")
            print(f"  Total duplicate jobs: {total_dup_jobs}")
        else:
            print("  No duplicates found")

        # 5. Data quality checks
        print("\n" + "=" * 60)
        print("DATA QUALITY CHECKS")
        print("=" * 60)

        missing_desc = await db.jobs.count_documents(
            {"$or": [{"description": ""}, {"description": None}]}
        )
        missing_company = await db.jobs.count_documents(
            {"$or": [{"company": ""}, {"company": None}]}
        )
        missing_url = await db.jobs.count_documents(
            {"$or": [{"apply_url": ""}, {"apply_url": None}]}
        )

        issues = []
        if missing_desc > 0:
            issues.append(f"Missing descriptions: {missing_desc}")
        if missing_company > 0:
            issues.append(f"Missing companies: {missing_company}")
        if missing_url > 0:
            issues.append(f"Missing apply URLs: {missing_url}")

        if issues:
            print("  Issues found:")
            for issue in issues:
                print(f"    - {issue}")
        else:
            print("  All jobs have required fields")

        # 6. Top companies
        print("\n" + "=" * 60)
        print("TOP 10 COMPANIES")
        print("=" * 60)

        top_pipeline = [
            {"$group": {"_id": "$company", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10},
        ]
        async for doc in db.jobs.aggregate(top_pipeline):
            print(f"  {doc['_id'][:40]:40s}: {doc['count']:3,} jobs")

        # 7. Employment types
        print("\n" + "=" * 60)
        print("EMPLOYMENT TYPES")
        print("=" * 60)

        emp_pipeline = [
            {"$group": {"_id": "$employment_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]
        async for doc in db.jobs.aggregate(emp_pipeline):
            emp_type_str = doc["_id"] or "Not specified"
            percentage = (doc["count"] / total_jobs) * 100
            print(f"  {emp_type_str:20s}: {doc['count']:5,} ({percentage:5.1f}%)")

        # 8. Remote vs On-site
        print("\n" + "=" * 60)
        print("REMOTE JOBS")
        print("=" * 60)

        remote_count = await db.jobs.count_documents({"is_remote": True})
        remote_percentage = (remote_count / total_jobs) * 100
        print(f"  Remote: {remote_count:,} ({remote_percentage:.1f}%)")
        print(f"  On-site: {total_jobs - remote_count:,} ({100 - remote_percentage:.1f}%)")

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        score = 100
        if missing_desc > 0:
            score -= 10
        if missing_company > 0:
            score -= 15
        if missing_url > 0:
            score -= 20
        if len(duplicates) > 10:
            score -= 15

        if score >= 90:
            status = "EXCELLENT"
        elif score >= 75:
            status = "GOOD"
        elif score >= 60:
            status = "FAIR"
        else:
            status = "NEEDS ATTENTION"

        print(f"\n  Data Quality Score: {score}/100")
        print(f"  Status: {status}")

        if score < 90:
            print("\n  Recommendations:")
            if missing_desc > 0:
                print("    - Review jobs with missing descriptions")
            if missing_company > 0:
                print("    - Investigate jobs with missing company names")
            if missing_url > 0:
                print("    - Check jobs with missing application URLs")
            if len(duplicates) > 10:
                print("    - Run deduplication cleanup")

    finally:
        await db.disconnect()

    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(validate_data())
