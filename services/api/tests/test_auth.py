"""Tests: authentication is required on all v1 endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.parametrize(
    "path",
    [
        "/v1/panchang/daily?date=2025-01-14&lat=28.6139&lon=77.2090&tz=Asia/Kolkata",
        "/v1/festivals",
        "/v1/notes",
        "/v1/profile",
        "/v1/subscription",
    ],
)
async def test_unauthenticated_returns_401(client: AsyncClient, path: str) -> None:
    response = await client.get(path)
    assert response.status_code == 401, f"Expected 401 for {path}, got {response.status_code}"


async def test_invalid_token_returns_401(client: AsyncClient) -> None:
    response = await client.get(
        "/v1/subscription",
        headers={"Authorization": "Bearer not.a.valid.token"},
    )
    assert response.status_code == 401


async def test_valid_token_passes_auth(client: AsyncClient, basic_token: str) -> None:
    """A valid JWT reaches the endpoint (may return non-200 for other reasons, but not 401)."""
    response = await client.get(
        "/v1/subscription",
        headers={"Authorization": f"Bearer {basic_token}"},
    )
    assert response.status_code != 401


async def test_expired_token_returns_401(client: AsyncClient) -> None:
    import time

    import jwt

    from api.settings import get_settings

    settings = get_settings()
    expired = jwt.encode(
        {"sub": "u1", "tier": "basic", "exp": int(time.time()) - 10},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    response = await client.get(
        "/v1/subscription",
        headers={"Authorization": f"Bearer {expired}"},
    )
    assert response.status_code == 401
