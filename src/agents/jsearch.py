import asyncio
from typing import Any, Dict, List

import aiohttp

from src.agents import BaseFetcher
from src.utils.config import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class JSearchFetcher(BaseFetcher):
    """Fetcher for JSearch via RapidAPI."""

    BASE_URL = "https://jsearch.p.rapidapi.com/search"
    
    # Broad IT/tech queries to capture ALL tech jobs
    QUERIES = [
        "software engineer",
        "software developer",
        "backend engineer",
        "backend developer",
        "frontend engineer",
        "frontend developer",
        "full stack developer",
        "devops engineer",
        "site reliability engineer",
        "cloud engineer",
        "platform engineer",
        "data engineer",
        "data scientist",
        "machine learning engineer",
        "AI engineer",
        "mobile developer",
        "iOS developer",
        "android developer",
        "QA engineer",
        "test engineer",
        "security engineer",
        "cybersecurity",
        "network engineer",
        "systems engineer",
        "database administrator",
        "solutions architect",
        "cloud architect",
        "technical lead",
        "engineering manager",
        "product engineer",
        "embedded engineer",
        "firmware engineer",
        "golang developer",
        "python developer",
        "java developer",
        "rust developer",
        "react developer",
        "node.js developer",
    ]
    
    MAX_PAGES = 5  # Pages per query

    def __init__(self) -> None:
        super().__init__("jsearch")
        self.api_key = settings.rapidapi_key
        if not self.api_key:
            logger.warning("[%s] RAPIDAPI_KEY missing; fetcher will return zero jobs", self.source_name)

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        if not self.api_key:
            return []

        logger.info("[%s] Fetching ALL IT/tech jobs (%d queries, %d pages each)", 
                     self.source_name, len(self.QUERIES), self.MAX_PAGES)
        results: List[Dict[str, Any]] = []

        async with aiohttp.ClientSession() as session:
            for query in self.QUERIES:
                query_jobs = await self._fetch_query(session, query)
                results.extend(query_jobs)
                await asyncio.sleep(1)  # stay within rate limits

        logger.info("[%s] Fetched %d total raw jobs (ALL - no filtering)", self.source_name, len(results))
        return results

    async def _fetch_query(self, session: aiohttp.ClientSession, query: str) -> List[Dict[str, Any]]:
        all_jobs: List[Dict[str, Any]] = []
        
        for page in range(1, self.MAX_PAGES + 1):
            params = {
                "query": query,
                "page": str(page),
                "num_pages": "1",
                "date_posted": "month",
            }
            headers = {
                "X-RapidAPI-Key": self.api_key,
                "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
            }

            try:
                async with session.get(self.BASE_URL, params=params, headers=headers, timeout=30) as response:
                    if response.status == 429:
                        logger.warning("[%s] Rate limited on query '%s' page %d, stopping query", 
                                      self.source_name, query, page)
                        break
                    if response.status != 200:
                        logger.error("[%s] HTTP %s for query '%s' page %d", 
                                    self.source_name, response.status, query, page)
                        break

                    payload = await response.json()
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("[%s] Request error for query '%s' page %d: %s", 
                            self.source_name, query, page, exc, exc_info=True)
                break

            data = payload.get("data", [])
            if not data:
                break
            
            # Return raw data with query context
            for job in data:
                job['_jsearch_query'] = query
                job['_jsearch_page'] = page
                all_jobs.append(job)
            
            logger.debug("[%s] Fetched %d jobs for '%s' page %d", self.source_name, len(data), query, page)
            await asyncio.sleep(0.5)  # Delay between pages

        return all_jobs
