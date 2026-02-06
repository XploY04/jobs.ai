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

    # App settings
    environment: str = "development"
    log_level: str = "INFO"
    api_port: int = 8000
    ingestion_interval_minutes: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
