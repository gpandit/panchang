"""
Smoke tests for the API gateway.

These run in CI on every push. They exercise the FastAPI app in-process
(no real database, Redis or downstream services needed) to verify the
basic wiring is correct.
"""

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client():  # type: ignore[return]
    from api.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_health_returns_ok(client: AsyncClient) -> None:
    """GET /health should return 200 with status=ok."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["environment"] in {"development", "staging", "production"}


def test_settings_load() -> None:
    """Settings must load successfully with dev defaults."""
    from api.settings import get_settings

    s = get_settings()
    assert s.port == 8000
    assert s.environment == "development"
