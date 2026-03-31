from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from src.api.routes import router
from src.database.operations import db
from src.utils.config import settings


def create_app() -> FastAPI:
    """FastAPI application factory."""

    app = FastAPI(title="Backend & DevOps Jobs API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.environment != "production" else [
            os.getenv("FRONTEND_URL", "https://jobs-ai.vercel.app"),
        ],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def startup_event() -> None:
        await db.connect()

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        await db.disconnect()

    app.include_router(router)
    return app


app = create_app()
