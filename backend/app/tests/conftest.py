"""Shared pytest fixtures for backend tests.

Provides:
- TestFastAPIClient: Async test client for FastAPI routes
- db_session: In-memory database session override
- user_factory: Factory to create test user instances
- mock_auth: Dependency overrides for auth injection
- reset_secret_key: Autouse fixture to reset JWT secret between tests
"""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import set_secret_key


# --- Fixtures ---


@pytest.fixture(autouse=True)
def reset_secret_key() -> None:
    """Reset the JWT secret key before each test to ensure isolation."""
    from app.core.auth import _SECRET_KEY  # noqa: PLC0414

    yield

    # Reset after each test
    set_secret_key(_SECRET_KEY)


@pytest.fixture
def jwt_secret() -> str:
    """Provide a consistent test JWT secret key.

    Returns:
        A fixed secret key for token operations during tests.
    """
    return "test-secret-key-for-unit-tests"


@pytest.fixture(autouse=True)
def configure_jwt(jwt_secret: str) -> None:
    """Configure JWT to use the test secret key."""
    set_secret_key(jwt_secret)


# --- Database fixtures (for when SQLAlchemy models exist) ---


@pytest.fixture
def engine():
    """Create an in-memory SQLite engine for fast unit tests.

    Uses StaticPool for thread safety and check_same_thread=False
    to allow usage across async contexts.
    """
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return eng


@pytest.fixture
def session_factory(engine):
    """Create a session factory bound to the in-memory engine."""
    return sessionmaker(bind=engine)


@pytest.fixture
def db_session(session_factory) -> AsyncGenerator:
    """Provide a transactional database session that rolls back after each test.

    Usage in tests:
        async def test_something(db_session):
            user = User(name="test")
            db_session.add(user)
            await db_session.commit()
            # assertions here
    """
    from sqlalchemy import event  # noqa: PLC0414

    with engine.connect() as connection:
        @event.listens_for(connection, "begin")
        def do_begin() -> None:  # noqa: PT004
            pass

        Session = sessionmaker(bind=connection)
        session = Session()

        yield session

        session.rollback()
        session.close()


# --- User factory fixtures ---


@pytest.fixture
def user_factory():
    """Factory fixture to create test user dictionaries.

    Usage:
        def test_something(user_factory):
            user = user_factory(email="test@example.com")
    """

    def _create(
        user_id: str = "00000000-0000-0000-0000-000000000001",
        email: str = "test@example.com",
        hashed_password: str | None = None,
        is_active: bool = True,
        role: str = "admin",
    ) -> dict:
        import uuid  # noqa: PLC0414

        if hashed_password is None:
            from app.core.auth import hash_password  # noqa: PLC0414

            hashed_password = hash_password("testpassword")

        return {
            "id": user_id,
            "email": email,
            "hashed_password": hashed_password,
            "is_active": is_active,
            "role": role,
        }

    return _create


# --- Auth dependency mock fixture ---


@pytest.fixture
def mock_auth_context():
    """Provide a mock authentication context for testing auth-dependent routes.

    Returns a dictionary of mock claims that can be used to test
    protected endpoints without real authentication.

    Usage:
        async def test_protected_route(mock_auth_context, test_client):
            response = await test_client.get("/protected", cookies=...)
            assert response.status_code == 200
    """
    return {
        "sub": "test-user-id",
        "role": "admin",
        "email": "test@example.com",
    }


# --- FastAPI test client fixture (for when routes exist) ---


@pytest.fixture
async def test_client_fixture() -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP test client for the FastAPI application.

    NOTE: This requires app/main.py to exist. If testing only
    utilities without routes, use auth/audit specific fixtures instead.
    """
    try:
        from app.main import app  # noqa: PLC0414

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    except ImportError:
        # Skip if app doesn't exist yet — used by CI when only utility tests run
        pytest.skip("FastAPI app not available")


# --- Configuration fixture for environment variables ---


@pytest.fixture
def env_config():
    """Context manager for setting and cleaning up environment variables during tests."""
    import os  # noqa: PLC0414

    original_env = {}

    def _set(**kwargs) -> None:  # noqa: ANN001, PT004
        for key, value in kwargs.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = str(value)

    yield _set

    # Restore
    for key in original_env:
        if original_env[key] is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_env[key]
