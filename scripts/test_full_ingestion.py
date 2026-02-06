"""Test full ingestion cycle with all sources including new ones"""

import asyncio
from src.services.ingestion import run_ingestion_cycle
from src.database.operations import db
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def main():
    """Run one ingestion cycle with all sources"""
    print("\n" + "="*60)
    print("FULL INGESTION CYCLE TEST")
    print("Testing: RemoteOK, JSearch, Adzuna, HackerNews, RSS Feeds")
    print("="*60 + "\n")
    
    # Ensure database is connected
    await db.connect()
    
    try:
        # Run ingestion
        summary = await run_ingestion_cycle()
        
        # Display results
        print("\n" + "="*60)
        print("INGESTION SUMMARY")
        print("="*60)
        print(f"\nJobs per source:")
        for source, count in summary['sources'].items():
            print(f"  {source:20s}: {count:4d} jobs")
        
        print(f"\nTotal fetched: {summary['total_jobs']}")
        print(f"New in DB:     {summary['db']['new']}")
        print(f"Skipped:       {summary['db']['skipped']}")
        print(f"\nRan at: {summary['ran_at']}")
        
        print("\n✓ Ingestion cycle complete!")
        
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
