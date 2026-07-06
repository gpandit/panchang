"""Tests for F4 — marketplace module skeleton + router registration.

Verifies the acceptance criteria from ``docs/dev-plan-marketplace.md`` step F4:

* ``GET /v1/marketplace/healthz`` returns 200 (no auth required — a bare
  liveness probe for the whole marketplace domain, mirroring ``/health``).
* the same probe exists on the admin namespace (``/admin/v1/marketplace/healthz``).
* the OpenAPI schema exposes the new ``/v1/marketplace...`` paths and the
  ``marketplace`` tag, so ``packages/api-client-ts`` has a contract to regenerate
  against.
"""

from __future__ import annotations

from httpx import AsyncClient


async def test_marketplace_healthz_returns_ok(client: AsyncClient) -> None:
    r = await client.get("/v1/marketplace/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_admin_marketplace_healthz_returns_ok(client: AsyncClient) -> None:
    r = await client.get("/admin/v1/marketplace/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_openapi_includes_marketplace_healthz_path(client: AsyncClient) -> None:
    schema = (await client.get("/openapi.json")).json()
    assert "/v1/marketplace/healthz" in schema["paths"]


async def test_openapi_includes_marketplace_tag(client: AsyncClient) -> None:
    schema = (await client.get("/openapi.json")).json()
    path_item = schema["paths"]["/v1/marketplace/healthz"]["get"]
    assert "marketplace" in path_item["tags"]
