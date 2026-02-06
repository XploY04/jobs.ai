"""Job ingestion orchestration and scheduling utilities."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.agents.adzuna import AdzunaFetcher
from src.agents.jsearch import JSearchFetcher
from src.agents.remoteok import RemoteOKFetcher
from src.database.operations import db
from src.enrichment.enrichment_pipeline import EnrichmentPipeline
from src.utils.config import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

FETCHER_CLASSES = [RemoteOKFetcher, JSearchFetcher, AdzunaFetcher]

# Initialize enrichment pipeline
enrichment_pipeline = EnrichmentPipeline(use_ai=settings.enable_ai_enrichment)


async def run_ingestion_cycle() -> Dict[str, Any]:
    """Fetch jobs from all sources and persist them."""

    fetchers = [fetcher_cls() for fetcher_cls in FETCHER_CLASSES]
    results = await asyncio.gather(*(_collect_jobs(fetcher) for fetcher in fetchers))

    all_jobs: List[Dict[str, Any]] = []
    per_source: Dict[str, int] = {}

    for source_name, jobs in results:
        per_source[source_name] = len(jobs)
        all_jobs.extend(jobs)

    # Enrich jobs before saving to database
    if all_jobs and settings.enable_ai_enrichment:
        logger.info(f"Enriching {len(all_jobs)} jobs...")
        try:
            all_jobs = enrichment_pipeline.enrich_batch(all_jobs)
            logger.info("Enrichment complete")
        except Exception as e:
            logger.error(f"Enrichment failed: {e}")
            # Continue with unenriched jobs

    db_stats = await db.save_jobs(all_jobs) if all_jobs else {"new": 0, "skipped": 0}

    summary = {
        "sources": per_source,
        "db": db_stats,
        "total_jobs": len(all_jobs),
        "ran_at": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(
        "Ingestion finished | total=%s new=%s skipped=%s", summary["total_jobs"], db_stats["new"], db_stats["skipped"]
    )
    return summary


async def _collect_jobs(fetcher: RemoteOKFetcher | JSearchFetcher | AdzunaFetcher) -> Tuple[str, List[Dict[str, Any]]]:
    try:
        jobs = await fetcher.fetch_jobs()
        return fetcher.source_name, jobs
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("[%s] Fetch failure: %s", fetcher.source_name, exc, exc_info=True)
        return fetcher.source_name, []


class IngestionScheduler:
    """APS-based scheduler that triggers ingestion cycles."""

    def __init__(self, interval_minutes: int | None = None) -> None:
        self.interval_minutes = interval_minutes or settings.ingestion_interval_minutes
        self.scheduler = AsyncIOScheduler()
        self.job_id = "job_ingestion_cycle"

    def start(self) -> None:
        if self.scheduler.running:
            return

        self.scheduler.add_job(
            self._run_cycle,
            "interval",
            minutes=self.interval_minutes,
            id=self.job_id,
            max_instances=1,
            replace_existing=True,
            next_run_time=datetime.now(timezone.utc),
        )
        self.scheduler.start()
        logger.info("Scheduler started with %s-minute interval", self.interval_minutes)

    def stop(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    async def _run_cycle(self) -> None:
        await run_ingestion_cycle()

    async def run_once(self) -> Dict[str, Any]:
        return await run_ingestion_cycle()
