import asyncio
from typing import Any, Dict, List

import aiohttp

from src.agents import BaseFetcher
from src.utils.config import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class AdzunaFetcher(BaseFetcher):
    """Fetcher for Adzuna API."""

    BASE_URL_TEMPLATE = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
    COUNTRIES = ["us", "gb", "ca", "au", "de", "fr", "nl"]
    CATEGORY = "it-jobs"
    MAX_PAGES = 20  # 20 pages × 100 results = 2000 jobs per country

    def __init__(self) -> None:
        super().__init__("adzuna")
        self.app_id = settings.adzuna_app_id
        self.app_key = settings.adzuna_api_key
        if not (self.app_id and self.app_key):
            logger.warning("[%s] Adzuna credentials missing; fetcher will skip", self.source_name)

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        if not (self.app_id and self.app_key):
            return []

        logger.info("[%s] Fetching jobs from %d countries with pagination", self.source_name, len(self.COUNTRIES))
        collected: List[Dict[str, Any]] = []

        async with aiohttp.ClientSession() as session:
            for country in self.COUNTRIES:
                country_jobs = await self._fetch_country(session, country)
                collected.extend(country_jobs)
                logger.info("[%s] Collected %d jobs from %s", self.source_name, len(country_jobs), country.upper())
                await asyncio.sleep(0.5)

        logger.info("[%s] Total jobs collected: %d (NO FILTERING - all jobs)", self.source_name, len(collected))
        return collected

    async def _fetch_country(self, session: aiohttp.ClientSession, country: str) -> List[Dict[str, Any]]:
        """Fetch jobs from a country with pagination - returns RAW data with all fields"""
        all_jobs: List[Dict[str, Any]] = []
        
        for page in range(1, self.MAX_PAGES + 1):
            url = self.BASE_URL_TEMPLATE.format(country=country, page=page)
            params = {
                "app_id": self.app_id,
                "app_key": self.app_key,
                "results_per_page": 100,  # Maximum allowed by Adzuna API
                "category": self.CATEGORY,
                "sort_by": "date",
            }

            try:
                async with session.get(url, params=params, timeout=30) as response:
                    if response.status != 200:
                        logger.error("[%s] HTTP %s for %s page %d", self.source_name, response.status, country, page)
                        break
                    payload = await response.json()
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("[%s] Request error for %s page %d: %s", self.source_name, country, page, exc)
                break

            results = payload.get("results", [])
            if not results:
                logger.info("[%s] No more results for %s at page %d", self.source_name, country, page)
                break
            
            # Return RAW data with ALL fields - no normalization here
            # Add metadata for context
            for job in results:
                job['_adzuna_country'] = country  # Add country context
                job['_adzuna_page'] = page  # Add page context for debugging
                all_jobs.append(job)
            
            logger.debug("[%s] Fetched %d jobs from %s page %d", self.source_name, len(results), country, page)
            
            # Small delay between pages to avoid rate limiting
            await asyncio.sleep(0.2)
        
        return all_jobs
