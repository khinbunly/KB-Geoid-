"""Application configuration module."""

from pathlib import Path
from typing import Literal, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram Bot Token
    TELEGRAM_BOT_TOKEN: str = Field(
        default="8907224822:AAET1E4Eb2h_MYHd-8qJ6kXCt_DLqDzTuAo",
        description="Telegram bot token from @BotFather",
    )

    # Environment & Logging
    APP_ENV: Literal["development", "production", "testing"] = "production"
    LOG_LEVEL: str = "INFO"
    LOG_DIR: Path = Path("logs")

    # Geoid Engine
    GEOID_BACKEND: Literal["auto", "proj", "geographiclib"] = "auto"
    PROJ_NETWORK: bool = True
    PROJ_CACHE_DIR: Path = Path(".proj_cache")

    # Upload & Processing Limits
    MAX_UPLOAD_SIZE_MB: int = 20
    MAX_BATCH_ROWS: int = 50000

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Base directory
    BASE_DIR: Path = Path(__file__).resolve().parent.parent


# Global singleton settings instance
settings = Settings()
