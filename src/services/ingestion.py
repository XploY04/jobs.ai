"""Job ingestion orchestration and scheduling utilities."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.agents.adzuna import AdzunaFetcher
from src.agents.jsearch import JSearchFetcher
from src.agents.remoteok import RemoteOKFetcher
from src.agents.hackernews import HackerNewsFetcher
from src.agents.rss_feed import RSSFeedFetcher
from src.agents.ats_scraper import ATSScraperFetcher
from src.database.operations import db
from src.enrichment.enrichment_pipeline import EnrichmentPipeline
from src.utils.config import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

FETCHER_CLASSES = [RemoteOKFetcher, JSearchFetcher, AdzunaFetcher, HackerNewsFetcher, RSSFeedFetcher, ATSScraperFetcher]

# Single pipeline: Raw → AI → Structured (no normalizer)
pipeline = EnrichmentPipeline(use_ai=settings.enable_ai_enrichment)


async def run_ingestion_cycle() -> Dict[str, Any]:
    """Fetch raw → AI process → Save per batch. Each batch of ~5 jobs
    hits the DB as soon as Gemini finishes processing it."""

    fetchers = [fetcher_cls() for fetcher_cls in FETCHER_CLASSES]
    results = await asyncio.gather(*(_collect_jobs(fetcher) for fetcher in fetchers))

    # Thread-safe counters (only mutated inside async tasks, one event loop)
    per_source: Dict[str, Dict[str, Any]] = {}
    total_new = 0
    total_skipped = 0
    total_processed = 0

    async def _process_source(source_name: str, raw_jobs: List[Dict[str, Any]]) -> None:
        nonlocal total_new, total_skipped, total_processed

        if not raw_jobs:
            per_source[source_name] = {"raw": 0, "processed": 0, "new": 0, "skipped": 0}
            return

        source_stats = {"new": 0, "skipped": 0}

        async def _save_batch(batch: List[Dict[str, Any]]) -> None:
            """Called by the pipeline after each batch (~5 jobs) is processed."""
            stats = await db.save_jobs(batch)
            source_stats["new"] += stats["new"]
            source_stats["skipped"] += stats["skipped"]
            logger.info("[%s] Batch saved — new=%d skipped=%d", source_name, stats["new"], stats["skipped"])

        try:
            processed = await pipeline.process_source(
                source_name, raw_jobs, on_batch_ready=_save_batch
            )

            per_source[source_name] = {
                "raw": len(raw_jobs),
                "processed": len(processed),
                "new": source_stats["new"],
                "skipped": source_stats["skipped"],
            }
            total_new += source_stats["new"]
            total_skipped += source_stats["skipped"]
            total_processed += len(processed)

            logger.info("[%s] Done — raw=%d processed=%d new=%d skipped=%d",
                        source_name, len(raw_jobs), len(processed),
                        source_stats["new"], source_stats["skipped"])

        except Exception as exc:
            logger.error("[%s] Failed: %s", source_name, exc, exc_info=True)
            per_source[source_name] = {"raw": len(raw_jobs), "processed": 0, "new": 0, "skipped": 0, "error": str(exc)}

    # Process ALL sources concurrently — each batch saves independently
    await asyncio.gather(
        *(_process_source(name, jobs) for name, jobs in results)
    )

    summary = {
        "sources": per_source,
        "db": {"new": total_new, "skipped": total_skipped},
        "total_jobs": total_processed,
        "ran_at": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(
        "Ingestion finished | total=%d new=%d skipped=%d", total_processed, total_new, total_skipped
    )
    return summary


async def _collect_jobs(fetcher) -> Tuple[str, List[Dict[str, Any]]]:
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
