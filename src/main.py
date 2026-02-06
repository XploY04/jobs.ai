"""Application entrypoint and lightweight CLI."""

import argparse
import asyncio
import json

import uvicorn

from src.api.main import app  # noqa: F401  (exposed for uvicorn)
from src.database.operations import db
from src.services.ingestion import run_ingestion_cycle
from src.utils.config import settings


async def _run_ingestion_once() -> dict:
    await db.connect()
    summary = await run_ingestion_cycle()
    await db.disconnect()
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Backend & DevOps job aggregator")
    parser.add_argument(
        "--ingest-once",
        action="store_true",
        help="Run a single ingestion cycle then exit",
    )

    args = parser.parse_args()

    if args.ingest_once:
        summary = asyncio.run(_run_ingestion_once())
        print(json.dumps(summary, indent=2))  # noqa: T201
        return

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=settings.environment != "production",
    )


if __name__ == "__main__":
    main()
