"""Offline API security boundary tests.

These checks use the in-process FastAPI app and deterministic development
settings.  They never require a real JWT issuer, database, cache, or secret.
"""

from __future__ import annotations

from httpx import AsyncClient


async def test_health_and_healthz_are_liveness_only(client: AsyncClient) -> None:
    for path in ("/health", "/healthz"):
        response = await client.get(path)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert set(response.json()) == {"status", "environment"}


async def test_debug_docs_are_disabled_by_default(client: AsyncClient) -> None:
    assert (await client.get("/docs")).status_code == 404
    assert (await client.get("/redoc")).status_code == 404


async def test_protected_route_rejects_missing_credentials(client: AsyncClient) -> None:
    response = await client.get("/v1/profile")
    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"


def test_non_debug_cors_never_returns_wildcard() -> None:
    from api.settings import Settings

    settings = Settings(debug=False, allowed_origins="https://pandit.example")
    assert "*" not in settings.allowed_origins_list
    assert settings.allowed_origins_list == ["https://pandit.example"]


def test_internal_adapter_token_is_not_in_openapi() -> None:
    from api.main import app

    schema = app.openapi()
    assert "subscription_adapter_token" not in str(schema).lower()
