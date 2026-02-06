"""RSS feed reader for job boards"""

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import aiohttp
import feedparser

from src.agents import BaseFetcher
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class RSSFeedFetcher(BaseFetcher):
    """
    Generic RSS feed fetcher for job boards.
    
    Supports common job board RSS feeds like:
    - Stack Overflow Jobs RSS
    - GitHub Jobs RSS  
    - Indie Hackers job board
    - We Work Remotely RSS
    - Other RSS/Atom feeds with job listings
    """

    # Curated list of backend/devops job RSS feeds
    DEFAULT_FEEDS = [
        "https://stackoverflow.com/jobs/feed?q=backend+engineer&r=true",
        "https://stackoverflow.com/jobs/feed?q=devops+engineer&r=true", 
        "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
        "https://remoteok.com/remote-backend-jobs.rss",
        "https://remoteok.com/remote-devops-jobs.rss",
    ]

    def __init__(self, feed_urls: Optional[List[str]] = None) -> None:
        super().__init__("rss_feed")
        self.feed_urls = feed_urls or self.DEFAULT_FEEDS

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """Fetch jobs from all configured RSS feeds"""
        logger.info("[%s] Fetching from %d RSS feeds", self.source_name, len(self.feed_urls))
        
        all_jobs = []
        async with aiohttp.ClientSession() as session:
            for feed_url in self.feed_urls:
                jobs = await self._fetch_feed(session, feed_url)
                all_jobs.extend(jobs)
        
        # Deduplicate by source_id
        seen_ids = set()
        unique_jobs = []
        for job in all_jobs:
            if job["source_id"] not in seen_ids:
                seen_ids.add(job["source_id"])
                unique_jobs.append(job)
        
        logger.info("[%s] Found %d unique jobs from %d feeds", self.source_name, len(unique_jobs), len(self.feed_urls))
        return unique_jobs

    async def _fetch_feed(self, session: aiohttp.ClientSession, feed_url: str) -> List[Dict[str, Any]]:
        """Fetch and parse a single RSS feed"""
        try:
            async with session.get(feed_url, timeout=30) as response:
                if response.status != 200:
                    logger.warning("[%s] HTTP %s for feed: %s", self.source_name, response.status, feed_url)
                    return []
                
                content = await response.text()
            
            # Parse with feedparser
            feed = feedparser.parse(content)
            
            if feed.bozo:  # Feed parsing error
                logger.warning("[%s] Parse error for feed: %s", self.source_name, feed_url)
                return []
            
            jobs = []
            for entry in feed.entries[:100]:  # Limit to 100 entries per feed
                job = self._parse_entry(entry, feed_url)
                if job and self.is_backend_devops_job(job["title"], job["description"]):
                    jobs.append(job)
            
            logger.info("[%s] Extracted %d jobs from: %s", self.source_name, len(jobs), feed_url)
            return jobs
            
        except Exception as exc:
            logger.error("[%s] Error fetching feed %s: %s", self.source_name, feed_url, exc, exc_info=True)
            return []

    def _parse_entry(self, entry: Any, feed_url: str) -> Optional[Dict[str, Any]]:
        """Parse an RSS entry into a normalized job dict"""
        try:
            # Extract basic fields
            title = entry.get("title", "").strip()
            if not title:
                return None
            
            # Get description from summary or content
            description = ""
            if hasattr(entry, "summary"):
                description = entry.summary
            elif hasattr(entry, "content") and entry.content:
                description = entry.content[0].value
            
            # Clean HTML from description
            description = self._strip_html(description)
            
            # Extract URL
            apply_url = entry.get("link", "")
            
            # Generate unique ID from URL or content
            if apply_url:
                source_id = hashlib.md5(apply_url.encode()).hexdigest()[:16]
            else:
                source_id = hashlib.md5((title + description[:100]).encode()).hexdigest()[:16]
            
            # Extract published date
            posted_at = self._parse_date(entry)
            
            # Try to extract company from title or description
            company = self._extract_company(title, description)
            
            # Extract location
            location = self._extract_location_from_entry(entry, title, description)
            
            return {
                "source": self.source_name,
                "source_id": source_id,
                "title": title[:200],
                "company": company[:100],
                "description": description[:5000],
                "location": {
                    "city": None,
                    "country": None,
                    "remote": "remote" in location.lower() if location else False,
                },
                "employment_type": "full-time",
                "salary_min": None,
                "salary_max": None,
                "apply_url": apply_url or "https://example.com",
                "posted_at": posted_at,
            }
            
        except Exception as exc:
            logger.warning("[%s] Error parsing entry: %s", self.source_name, exc)
            return None

    def _strip_html(self, text: str) -> str:
        """Remove HTML tags from text"""
        import re
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _parse_date(self, entry: Any) -> datetime:
        """Parse published date from entry"""
        # Try different date fields
        for date_field in ["published_parsed", "updated_parsed", "created_parsed"]:
            if hasattr(entry, date_field):
                date_tuple = getattr(entry, date_field)
                if date_tuple:
                    try:
                        import time
                        timestamp = time.mktime(date_tuple)
                        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
                    except Exception:
                        pass
        
        # Fallback to current time
        return datetime.now(timezone.utc)

    def _extract_company(self, title: str, description: str) -> str:
        """Try to extract company name from title or description"""
        import re
        
        # Pattern: "Company Name - Job Title" or "Job Title at Company Name"
        match = re.match(r"^([^-@]+?)\s*[-–—]\s*", title)
        if match:
            potential_company = match.group(1).strip()
            if 2 < len(potential_company) < 50 and not any(word in potential_company.lower() for word in ["engineer", "developer", "job", "senior", "junior"]):
                return potential_company
        
        match = re.search(r"\bat\s+([A-Z][a-zA-Z0-9\s&.,]+?)(?:\s*[-|]|\s*$)", title)
        if match:
            return match.group(1).strip()
        
        # Look in description for "Company:" or similar
        match = re.search(r"(?:Company|Organization|Employer):\s*([^\n]+)", description, re.IGNORECASE)
        if match:
            company = match.group(1).strip()
            if 2 < len(company) < 100:
                return company
        
        return "See Description"

    def _extract_location_from_entry(self, entry: Any, title: str, description: str) -> str:
        """Extract location from entry"""
        import re
        
        # Check for REMOTE keyword
        text = f"{title} {description}"
        if re.search(r"\b(remote|work from home|wfh|distributed)\b", text, re.IGNORECASE):
            return "Remote"
        
        # Look for location in tags
        if hasattr(entry, "tags"):
            for tag in entry.tags:
                if "location" in tag.get("term", "").lower():
                    return tag.get("label", "See Description")
        
        # Look for location patterns in description
        match = re.search(r"(?:Location|Based in|Office in):\s*([^\n]+)", description, re.IGNORECASE)
        if match:
            return match.group(1).strip()[:100]
        
        # Look for city, state/country patterns
        match = re.search(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),\s*([A-Z]{2}|[A-Z][a-z]+)\b", description)
        if match:
            return f"{match.group(1)}, {match.group(2)}"
        
        return "See Description"
