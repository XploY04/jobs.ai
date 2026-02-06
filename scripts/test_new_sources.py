"""Test script for new data sources"""

import asyncio
from src.agents.hackernews import HackerNewsFetcher
from src.agents.rss_feed import RSSFeedFetcher
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def test_hackernews():
    """Test HackerNews scraper"""
    print("\n" + "="*60)
    print("TESTING HACKERNEWS SCRAPER")
    print("="*60 + "\n")
    
    fetcher = HackerNewsFetcher()
    jobs = await fetcher.fetch_jobs()
    
    print(f"✓ Fetched {len(jobs)} backend/devops jobs from HackerNews")
    
    if jobs:
        print("\nSample job:")
        sample = jobs[0]
        print(f"  Source: {sample['source']}")
        print(f"  Source ID: {sample['source_id']}")
        print(f"  Title: {sample['title']}")
        print(f"  Company: {sample['company']}")
        print(f"  Location: {sample['location']}")
        print(f"  Description: {sample['description'][:150]}...")
        print(f"  Apply URL: {sample['apply_url']}")
    
    return jobs


async def test_rss_feeds():
    """Test RSS feed reader"""
    print("\n" + "="*60)
    print("TESTING RSS FEED READER")
    print("="*60 + "\n")
    
    # Test with a smaller subset of feeds for quick testing
    test_feeds = [
        "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
        "https://remoteok.com/remote-backend-jobs.rss",
    ]
    
    fetcher = RSSFeedFetcher(feed_urls=test_feeds)
    jobs = await fetcher.fetch_jobs()
    
    print(f"✓ Fetched {len(jobs)} backend/devops jobs from {len(test_feeds)} RSS feeds")
    
    if jobs:
        print("\nSample job:")
        sample = jobs[0]
        print(f"  Source: {sample['source']}")
        print(f"  Source ID: {sample['source_id']}")
        print(f"  Title: {sample['title']}")
        print(f"  Company: {sample['company']}")
        print(f"  Location: {sample['location']}")
        print(f"  Description: {sample['description'][:150]}...")
        print(f"  Apply URL: {sample['apply_url']}")
    
    return jobs


async def main():
    """Run all tests"""
    try:
        # Test HackerNews
        hn_jobs = await test_hackernews()
        
        # Test RSS feeds
        rss_jobs = await test_rss_feeds()
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"HackerNews: {len(hn_jobs)} jobs")
        print(f"RSS Feeds: {len(rss_jobs)} jobs")
        print(f"Total: {len(hn_jobs) + len(rss_jobs)} jobs")
        print("\n✓ All tests passed!")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
