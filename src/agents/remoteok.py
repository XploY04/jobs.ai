from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiohttp
from dateutil import parser

from src.agents import BaseFetcher
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class RemoteOKFetcher(BaseFetcher):
    """Fetcher for RemoteOK public API."""

    API_URL = "https://remoteok.com/api"

    def __init__(self) -> None:
        super().__init__("remoteok")

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        logger.info("[%s] Fetching jobs", self.source_name)

        async with aiohttp.ClientSession() as session:
            headers = {"User-Agent": "JobAggregator/1.0"}
            async with session.get(self.API_URL, headers=headers, timeout=30) as response:
                if response.status != 200:
                    logger.error("[%s] HTTP %s", self.source_name, response.status)
                    return []

                data = await response.json()

        jobs = data[1:] if data else []  # first element is metadata
        normalized = []

        for job in jobs:
            if not self.is_backend_devops_job(job.get("position", ""), job.get("description", "")):
                continue

            normalized_job = self._normalize(job)
            if normalized_job:
                normalized.append(normalized_job)

        logger.info("[%s] Found %d backend/devops jobs", self.source_name, len(normalized))
        return normalized

    def _normalize(self, job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            epoch_value = job.get("epoch")
            date_value = job.get("date")
            if isinstance(epoch_value, (int, float)) or (isinstance(epoch_value, str) and epoch_value.isdigit()):
                posted = datetime.fromtimestamp(int(epoch_value), tz=timezone.utc)
            elif date_value:
                posted = parser.isoparse(str(date_value))
            else:
                posted = datetime.now(timezone.utc)

            return {
                "source": self.source_name,
                "source_id": str(job.get("id", "")),
                "title": job.get("position", ""),
                "company": job.get("company", ""),
                "description": job.get("description", ""),
                "location": {
                    "city": None,
                    "country": job.get("location", "Remote"),
                    "remote": True,
                },
                "employment_type": (job.get("type") or "FULLTIME").upper(),
                "salary_min": None,
                "salary_max": None,
                "salary_currency": "USD",
                "apply_url": job.get("url", ""),
                "posted_at": posted,
                "raw_data": job,
            }
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("[%s] Normalization error: %s", self.source_name, exc, exc_info=True)
            return None
