from typing import Any, Dict, List

import aiohttp

from src.agents import BaseFetcher
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class RemoteOKFetcher(BaseFetcher):
    """Fetcher for RemoteOK public API."""

    API_URL = "https://remoteok.com/api"

    def __init__(self) -> None:
        super().__init__("remoteok")

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        logger.info("[%s] Fetching ALL jobs (no filtering)", self.source_name)

        async with aiohttp.ClientSession() as session:
            headers = {"User-Agent": "JobAggregator/1.0"}
            async with session.get(self.API_URL, headers=headers, timeout=30) as response:
                if response.status != 200:
                    logger.error("[%s] HTTP %s", self.source_name, response.status)
                    return []

                data = await response.json()

        jobs = data[1:] if data else []  # first element is metadata

        # Return ALL raw jobs — no filtering, no normalization
        for job in jobs:
            job['_source'] = self.source_name  # Add source context

        logger.info("[%s] Fetched %d total jobs (ALL - no filtering)", self.source_name, len(jobs))
        return jobs
