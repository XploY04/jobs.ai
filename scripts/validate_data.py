#!/usr/bin/env python
"""
Data validation and quality checks for the jobs database.

Usage:
    python scripts/validate_data.py
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from collections import Counter

# Add src to path
sys.path.insert(0, '/app' if sys.platform == 'linux' else '.')

from src.database.operations import db
from src.database.models import Job
from sqlalchemy import select, func


async def validate_data():
    """Run comprehensive data validation checks"""
    
    print("=" * 60)
    print("JOB DATABASE VALIDATION REPORT")
    print("=" * 60)
    print(f"Generated: {datetime.now(timezone.utc).isoformat()}\n")
    
    await db.connect()
    
    try:
        # 1. Total jobs count
        async with db.session_maker() as session:
            result = await session.execute(select(func.count(Job.id)))
            total_jobs = result.scalar()
        
        print(f"📊 Total Jobs: {total_jobs:,}")
        
        if total_jobs == 0:
            print("\n⚠️  WARNING: No jobs found in database!")
            return
        
        # 2. Jobs per source
        print("\n" + "=" * 60)
        print("JOBS BY SOURCE")
        print("=" * 60)
        
        async with db.session_maker() as session:
            result = await session.execute(
                select(Job.source, func.count(Job.id))
                .group_by(Job.source)
                .order_by(func.count(Job.id).desc())
            )
            
            for source, count in result.all():
                percentage = (count / total_jobs) * 100
                print(f"  {source:12s}: {count:5,} ({percentage:5.1f}%)")
        
        # 3. Recent jobs (last 7 days)
        print("\n" + "=" * 60)
        print("RECENT JOBS (Last 7 Days)")
        print("=" * 60)
        
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        
        async with db.session_maker() as session:
            result = await session.execute(
                select(func.count(Job.id))
                .where(Job.posted_at >= seven_days_ago)
            )
            recent_count = result.scalar()
        
        recent_percentage = (recent_count / total_jobs) * 100
        print(f"  Recent: {recent_count:,} ({recent_percentage:.1f}% of total)")
        
        # 4. Check for duplicates
        print("\n" + "=" * 60)
        print("DUPLICATE ANALYSIS")
        print("=" * 60)
        
        async with db.session_maker() as session:
            # Count by title_company_hash
            result = await session.execute(
                select(Job.title_company_hash, func.count(Job.id))
                .group_by(Job.title_company_hash)
                .having(func.count(Job.id) > 1)
            )
            duplicates = result.all()
        
        if duplicates:
            print(f"  ⚠️  Found {len(duplicates)} duplicate groups")
            total_dup_jobs = sum(count - 1 for _, count in duplicates)
            print(f"  Total duplicate jobs: {total_dup_jobs}")
        else:
            print("  ✅ No duplicates found")
        
        # 5. Data quality checks
        print("\n" + "=" * 60)
        print("DATA QUALITY CHECKS")
        print("=" * 60)
        
        async with db.session_maker() as session:
            # Missing descriptions
            result = await session.execute(
                select(func.count(Job.id))
                .where((Job.description == "") | (Job.description.is_(None)))
            )
            missing_desc = result.scalar()
            
            # Missing companies
            result = await session.execute(
                select(func.count(Job.id))
                .where((Job.company == "") | (Job.company.is_(None)))
            )
            missing_company = result.scalar()
            
            # Missing apply URLs
            result = await session.execute(
                select(func.count(Job.id))
                .where((Job.apply_url == "") | (Job.apply_url.is_(None)))
            )
            missing_url = result.scalar()
        
        issues = []
        if missing_desc > 0:
            issues.append(f"Missing descriptions: {missing_desc}")
        if missing_company > 0:
            issues.append(f"Missing companies: {missing_company}")
        if missing_url > 0:
            issues.append(f"Missing apply URLs: {missing_url}")
        
        if issues:
            print("  ⚠️  Issues found:")
            for issue in issues:
                print(f"    - {issue}")
        else:
            print("  ✅ All jobs have required fields")
        
        # 6. Top companies
        print("\n" + "=" * 60)
        print("TOP 10 COMPANIES")
        print("=" * 60)
        
        async with db.session_maker() as session:
            result = await session.execute(
                select(Job.company, func.count(Job.id))
                .group_by(Job.company)
                .order_by(func.count(Job.id).desc())
                .limit(10)
            )
            
            for company, count in result.all():
                print(f"  {company[:40]:40s}: {count:3,} jobs")
        
        # 7. Employment types
        print("\n" + "=" * 60)
        print("EMPLOYMENT TYPES")
        print("=" * 60)
        
        async with db.session_maker() as session:
            result = await session.execute(
                select(Job.employment_type, func.count(Job.id))
                .group_by(Job.employment_type)
                .order_by(func.count(Job.id).desc())
            )
            
            for emp_type, count in result.all():
                emp_type_str = emp_type or "Not specified"
                percentage = (count / total_jobs) * 100
                print(f"  {emp_type_str:20s}: {count:5,} ({percentage:5.1f}%)")
        
        # 8. Remote vs On-site
        print("\n" + "=" * 60)
        print("REMOTE JOBS")
        print("=" * 60)
        
        async with db.session_maker() as session:
            # Get all jobs and check location
            result = await session.execute(select(Job.location))
            locations = result.scalars().all()
            
            remote_count = sum(1 for loc in locations if loc and loc.get("remote") is True)
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
            status = "✅ EXCELLENT"
        elif score >= 75:
            status = "✔️  GOOD"
        elif score >= 60:
            status = "⚠️  FAIR"
        else:
            status = "❌ NEEDS ATTENTION"
        
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
