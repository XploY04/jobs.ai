import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiohttp
from dateutil import parser

from src.agents import BaseFetcher
from src.utils.config import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class AdzunaFetcher(BaseFetcher):
    """Fetcher for Adzuna API."""

    BASE_URL_TEMPLATE = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"
    COUNTRIES = ["us", "gb"]
    CATEGORY = "it-jobs"

    def __init__(self) -> None:
        super().__init__("adzuna")
        self.app_id = settings.adzuna_app_id
        self.app_key = settings.adzuna_api_key
        if not (self.app_id and self.app_key):
            logger.warning("[%s] Adzuna credentials missing; fetcher will skip", self.source_name)

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        if not (self.app_id and self.app_key):
            return []

        logger.info("[%s] Fetching jobs", self.source_name)
        collected: List[Dict[str, Any]] = []

        async with aiohttp.ClientSession() as session:
            for country in self.COUNTRIES:
                country_jobs = await self._fetch_country(session, country)
                collected.extend(country_jobs)
                await asyncio.sleep(0.5)

        filtered = [job for job in collected if self.is_backend_devops_job(job["title"], job["description"])]
        logger.info("[%s] Found %d backend/devops jobs", self.source_name, len(filtered))
        return filtered

    async def _fetch_country(self, session: aiohttp.ClientSession, country: str) -> List[Dict[str, Any]]:
        url = self.BASE_URL_TEMPLATE.format(country=country)
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "results_per_page": 50,
            "category": self.CATEGORY,
            "sort_by": "date",
        }

        try:
            async with session.get(url, params=params, timeout=30) as response:
                if response.status != 200:
                    logger.error("[%s] HTTP %s for %s", self.source_name, response.status, country)
                    return []
                payload = await response.json()
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("[%s] Request error for %s: %s", self.source_name, country, exc, exc_info=True)
            return []

        normalized: List[Dict[str, Any]] = []
        for job in payload.get("results", []):
            normalized_job = self._normalize(job, country)
            if normalized_job:
                normalized.append(normalized_job)

        return normalized

    def _normalize(self, job: Dict[str, Any], country: str) -> Optional[Dict[str, Any]]:
        try:
            created_str = job.get("created")
            posted_at = parser.isoparse(created_str) if created_str else datetime.now(timezone.utc)

            return {
                "source": self.source_name,
                "source_id": str(job.get("id", "")),
                "title": job.get("title", ""),
                "company": job.get("company", {}).get("display_name", ""),
                "description": job.get("description", ""),
                "location": {
                    "city": job.get("location", {}).get("display_name"),
                    "country": country.upper(),
                    "remote": False,
                },
                "employment_type": (job.get("contract_type") or "FULLTIME").upper(),
                "salary_min": job.get("salary_min"),
                "salary_max": job.get("salary_max"),
                "salary_currency": "USD" if country == "us" else "GBP",
                "apply_url": job.get("redirect_url", ""),
                "posted_at": posted_at,
                "raw_data": job,
            }
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("[%s] Normalization error: %s", self.source_name, exc, exc_info=True)
            return None
