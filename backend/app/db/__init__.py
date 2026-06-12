"""SQLAlchemy 2.0 session factory and engine setup."""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.debug,  # Log raw SQL in debug mode
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an async session and ensures closure."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create all tables defined in models (for local dev / testing).
    In production, Alembic migrations are used instead."""
    from app.models.base import Base  # noqa: F401 — import to register models

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("All tables synced (dev-only; use alembic in production)")


async def close_db() -> None:
    """Dispose of the async engine connection pool."""
    await engine.dispose()
    logger.info("Database connection pool closed")
