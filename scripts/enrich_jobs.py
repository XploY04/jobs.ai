#!/usr/bin/env python
"""
Enrich existing jobs in the database with AI-powered insights

Usage:
    # Enrich all jobs
    python scripts/enrich_jobs.py
    
    # Enrich specific source
    python scripts/enrich_jobs.py --source jsearch
    
    # Use AI enrichment
    python scripts/enrich_jobs.py --use-ai
    
    # Dry run (show what would be enriched)
    python scripts/enrich_jobs.py --dry-run
"""

import asyncio
import sys
from datetime import datetime
import argparse

# Add src to path
sys.path.insert(0, '/app' if sys.platform == 'linux' else '.')

from src.database.operations import db
from src.database.models import Job
from src.enrichment.enrichment_pipeline import EnrichmentPipeline
from sqlalchemy import select, update
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def enrich_existing_jobs(
    source: str = None,
    use_ai: bool = False,
    dry_run: bool = False,
    limit: int = None
):
    """Enrich jobs already in the database"""
    
    logger.info("=" * 60)
    logger.info("JOB ENRICHMENT SCRIPT")
    logger.info("=" * 60)
    logger.info(f"AI Enrichment: {'ENABLED' if use_ai else 'DISABLED (rule-based only)'}")
    logger.info(f"Dry Run: {'YES' if dry_run else 'NO'}")
    if source:
        logger.info(f"Source Filter: {source}")
    if limit:
        logger.info(f"Limit: {limit} jobs")
    logger.info("")
    
    await db.connect()
    
    try:
        # Fetch jobs from database
        async with db.session_maker() as session:
            query = select(Job)
            
            if source:
                query = query.where(Job.source == source)
            
            if limit:
                query = query.limit(limit)
            
            result = await session.execute(query)
            jobs_from_db = result.scalars().all()
        
        if not jobs_from_db:
            logger.warning("No jobs found to enrich!")
            return
        
        logger.info(f"Found {len(jobs_from_db)} jobs to enrich")
        logger.info("")
        
        # Convert to dicts for enrichment
        jobs_dict = []
        for job in jobs_from_db:
            jobs_dict.append({
                'id': job.id,
                'source': job.source,
                'title': job.title,
                'company': job.company,
                'description': job.description,
                'location': job.location,
                'employment_type': job.employment_type.value if job.employment_type else None,
                'salary_min': job.salary_min,
                'salary_max': job.salary_max,
                'apply_url': job.apply_url,
                'posted_at': job.posted_at
            })
        
        # Initialize enrichment pipeline
        pipeline = EnrichmentPipeline(use_ai=use_ai)
        
        # Enrich jobs
        enriched_jobs = pipeline.enrich_batch(jobs_dict)
        
        # Show stats
        logger.info("")
        logger.info("=" * 60)
        logger.info("ENRICHMENT STATISTICS")
        logger.info("=" * 60)
        
        stats = pipeline.get_enrichment_stats(enriched_jobs)
        
        logger.info(f"Total Jobs: {stats['total_jobs']}")
        logger.info("")
        logger.info("Coverage:")
        for metric, value in stats['enrichment_coverage'].items():
            logger.info(f"  {metric:20s}: {value}")
        
        logger.info("")
        logger.info("Averages:")
        for metric, value in stats['averages'].items():
            logger.info(f"  {metric:20s}: {value}")
        
        # Show sample enriched job
        if enriched_jobs:
            logger.info("")
            logger.info("=" * 60)
            logger.info("SAMPLE ENRICHED JOB")
            logger.info("=" * 60)
            sample = enriched_jobs[0]
            logger.info(f"Title: {sample['title']}")
            logger.info(f"Company: {sample['company']}")
            logger.info(f"Category: {sample.get('ai_category', 'N/A')}")
            logger.info(f"Quality Score: {sample.get('ai_quality_score', 'N/A')}")
            logger.info(f"Urgency: {sample.get('ai_urgency', 'N/A')}")
            logger.info(f"Skills ({len(sample.get('skills', []))}): {', '.join(sample.get('skills', [])[:10])}")
            
            if sample.get('ai_extracted_deadline'):
                logger.info(f"Deadline: {sample['ai_extracted_deadline']} (confidence: {sample.get('ai_deadline_confidence', 'N/A')})")
            
            if use_ai and sample.get('ai_seniority'):
                logger.info(f"Seniority: {sample.get('ai_seniority')}")
                logger.info(f"Work Arrangement: {sample.get('ai_work_arrangement', 'N/A')}")
                logger.info(f"Visa Sponsorship: {sample.get('ai_visa_sponsorship', 'N/A')}")
        
        if dry_run:
            logger.info("")
            logger.info("=" * 60)
            logger.info("DRY RUN - No changes saved to database")
            logger.info("=" * 60)
            return
        
        # Update database with enriched data
        logger.info("")
        logger.info("=" * 60)
        logger.info("UPDATING DATABASE")
        logger.info("=" * 60)
        
        updated_count = 0
        
        async with db.session_maker() as session:
            for enriched in enriched_jobs:
                job_id = enriched['id']
                
                update_data = {
                    'skills': enriched.get('skills', []),
                    'ai_category': enriched.get('ai_category'),
                    'ai_quality_score': enriched.get('ai_quality_score'),
                    'ai_urgency': enriched.get('ai_urgency'),
                    'ai_extracted_deadline': enriched.get('ai_extracted_deadline'),
                    'ai_deadline_confidence': enriched.get('ai_deadline_confidence')
                }
                
                # Add AI-specific fields if present
                if enriched.get('ai_seniority'):
                    update_data['ai_seniority'] = enriched['ai_seniority']
                
                try:
                    stmt = (
                        update(Job)
                        .where(Job.id == job_id)
                        .values(**update_data)
                    )
                    await session.execute(stmt)
                    updated_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to update job {job_id}: {e}")
            
            await session.commit()
        
        logger.info(f"✓ Updated {updated_count}/{len(enriched_jobs)} jobs")
        logger.info("")
        logger.info("=" * 60)
        logger.info("ENRICHMENT COMPLETE")
        logger.info("=" * 60)
        
    finally:
        await db.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Enrich jobs with AI-powered insights')
    parser.add_argument('--source', type=str, help='Filter by source (jsearch, adzuna, remoteok)')
    parser.add_argument('--use-ai', action='store_true', help='Enable AI enrichment with Gemini')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be enriched without saving')
    parser.add_argument('--limit', type=int, help='Limit number of jobs to process')
    
    args = parser.parse_args()
    
    asyncio.run(enrich_existing_jobs(
        source=args.source,
        use_ai=args.use_ai,
        dry_run=args.dry_run,
        limit=args.limit
    ))
