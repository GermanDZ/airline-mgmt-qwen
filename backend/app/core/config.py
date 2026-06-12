"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All application configuration, sourced from env vars / .env file."""

    # Application
    app_name: str = "Airline Management System"
    debug: bool = False
    log_level: str = "INFO"

    # Database (PostgreSQL 15+)
    database_url: str = Field(
        default="postgresql+asyncpg://ams:ams_password@localhost:5432/ams",
        description="Async database URL for SQLAlchemy.",
    )
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # Redis (cache + queue)
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for cache and pub/sub.",
    )

    # JWT / Auth
    secret_key: str = Field(
        default="dev-secret-key-change-in-production-DO-NOT-COMMIT",
        description="Secret key for JWT signing (HS256).",
    )
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        description="Allowed CORS origins.",
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance (singleton per process)."""
    return Settings()
