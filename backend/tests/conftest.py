"""Shared pytest fixtures for backend tests."""

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings


# Create a test database engine (uses DATABASE_URL or defaults to sqlite for local)
TEST_DATABASE_URL = "postgresql+asyncpg://ams:ams_password@localhost:5432/ams_test"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    """Create and tear down test database tables."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        # Import all models to register them with metadata
        from app.models.base import Base  # noqa: F401
        from app.models.audit import AuditLogEntry  # noqa: F401
        from app.core.security import (  # noqa: F401
            UserModel,
            RoleModel,
            PermissionModel,
            UserRoleModel,
            RolePermissionModel,
        )

        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(setup_test_db) -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session."""
    factory = async_sessionmaker(bind=setup_test_db, class_=AsyncSession)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP test client for the FastAPI app."""
    from app.main import app

    # Override the DB dependency
    from app.db import async_session_factory as real_factory  # noqa: F401

    original_get_db = app.dependency_overrides.get(getattr(real_factory, "__call__", None))

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[override_get_db] = lambda: override_get_db.__code__.co_freevars[0]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Clean up overrides
    app.dependency_overrides.clear()
