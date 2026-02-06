import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiohttp
from dateutil import parser

from src.agents import BaseFetcher
from src.utils.config import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class JSearchFetcher(BaseFetcher):
    """Fetcher for JSearch via RapidAPI."""

    BASE_URL = "https://jsearch.p.rapidapi.com/search"
    BACKEND_DEVOPS_QUERIES = [
        "backend engineer",
        "backend developer",
        "devops engineer",
        "site reliability engineer",
        "cloud engineer",
        "platform engineer",
        "golang developer",
        "python backend",
    ]

    def __init__(self) -> None:
        super().__init__("jsearch")
        self.api_key = settings.rapidapi_key
        if not self.api_key:
            logger.warning("[%s] RAPIDAPI_KEY missing; fetcher will return zero jobs", self.source_name)

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        if not self.api_key:
            return []

        logger.info("[%s] Fetching jobs", self.source_name)
        results: List[Dict[str, Any]] = []

        async with aiohttp.ClientSession() as session:
            for query in self.BACKEND_DEVOPS_QUERIES:
                query_jobs = await self._fetch_query(session, query)
                results.extend(query_jobs)
                await asyncio.sleep(1)  # stay within rate limits

        logger.info("[%s] Found %d jobs", self.source_name, len(results))
        return results

    async def _fetch_query(self, session: aiohttp.ClientSession, query: str) -> List[Dict[str, Any]]:
        params = {
            "query": query,
            "page": "1",
            "num_pages": "1",
            "date_posted": "month",
        }
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        }

        try:
            async with session.get(self.BASE_URL, params=params, headers=headers, timeout=30) as response:
                if response.status != 200:
                    logger.error("[%s] HTTP %s for query '%s'", self.source_name, response.status, query)
                    return []

                payload = await response.json()
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("[%s] Request error for query '%s': %s", self.source_name, query, exc, exc_info=True)
            return []

        normalized = []
        for job in payload.get("data", []):
            normalized_job = self._normalize(job)
            if normalized_job and self.is_backend_devops_job(normalized_job["title"], normalized_job["description"]):
                normalized.append(normalized_job)

        return normalized

    def _normalize(self, job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            posted_str = job.get("job_posted_at_datetime_utc")
            posted_at = parser.isoparse(posted_str) if posted_str else datetime.now(timezone.utc)

            return {
                "source": self.source_name,
                "source_id": job.get("job_id", ""),
                "title": job.get("job_title", ""),
                "company": job.get("employer_name", ""),
                "description": job.get("job_description", ""),
                "location": {
                    "city": job.get("job_city"),
                    "country": job.get("job_country"),
                    "remote": job.get("job_is_remote", False),
                },
                "employment_type": (job.get("job_employment_type") or "FULLTIME").upper(),
                "salary_min": job.get("job_min_salary"),
                "salary_max": job.get("job_max_salary"),
                "salary_currency": job.get("job_salary_currency"),
                "apply_url": job.get("job_apply_link", ""),
                "posted_at": posted_at,
                "raw_data": job,
            }
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("[%s] Normalization error: %s", self.source_name, exc, exc_info=True)
            return None
