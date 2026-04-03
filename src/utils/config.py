from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str

    # API Keys
    rapidapi_key: Optional[str] = None
    adzuna_app_id: Optional[str] = None
    adzuna_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    pinecone_api_key: Optional[str] = None
    redis_url: Optional[str] = None
    serpapi_key: Optional[str] = None

    # Email (Gmail SMTP)
    email_user: Optional[str] = None
    email_password: Optional[str] = None
    candidate_app_url: str = "https://candidate.remotestar.io"

    # AI Enrichment
    enable_ai_enrichment: bool = True

    # App settings
    environment: str = "development"
    log_level: str = "INFO"
    port: int = 8000  # Railway/Render inject PORT
    api_port: int = 8000  # Legacy alias
    ingestion_interval_minutes: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
