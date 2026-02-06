from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from src.api.routes import router
from src.database.operations import db
from src.services.ingestion import IngestionScheduler
from src.utils.config import settings

scheduler = IngestionScheduler()


def create_app() -> FastAPI:
    """FastAPI application factory."""

    app = FastAPI(title="Backend & DevOps Jobs API", version="0.1.0")

    if settings.environment != "production":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.on_event("startup")
    async def startup_event() -> None:
        await db.connect()
        # Skip scheduler in test mode to avoid event loop issues
        if not os.getenv('DISABLE_SCHEDULER'):
            scheduler.start()

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        if not os.getenv('DISABLE_SCHEDULER'):
            scheduler.stop()
        await db.disconnect()

    app.include_router(router)
    return app


app = create_app()
