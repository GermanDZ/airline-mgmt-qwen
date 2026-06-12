"""Basic health check endpoint tests."""

from httpx import AsyncClient

from app.main import app


async def test_health_check(client: AsyncClient) -> None:
    """Health endpoint returns 200 with status ok."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


async def test_openapi_schema(client: AsyncClient) -> None:
    """OpenAPI schema is available."""
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "Airline Management System"
