"""Tests: OpenAPI schema generates and is well-formed."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


async def test_openapi_schema_is_available(client: AsyncClient) -> None:
    """GET /openapi.json must return a valid OpenAPI 3.x document."""
    r = await client.get("/openapi.json")
    assert r.status_code == 200
    schema = r.json()
    assert schema.get("openapi", "").startswith("3.")
    assert "info" in schema
    assert "paths" in schema


async def test_openapi_includes_v1_panchang_path(client: AsyncClient) -> None:
    r = await client.get("/openapi.json")
    paths = r.json()["paths"]
    assert "/v1/panchang/daily" in paths


async def test_openapi_includes_auth_scheme(client: AsyncClient) -> None:
    schema = (await client.get("/openapi.json")).json()
    components = schema.get("components", {})
    security_schemes = components.get("securitySchemes", {})
    # FastAPI registers HTTPBearer under some key
    assert any(
        v.get("type") == "http" and v.get("scheme") == "bearer"
        for v in security_schemes.values()
    ), f"No bearer scheme found in securitySchemes: {security_schemes}"


async def test_openapi_all_v1_endpoints_present(client: AsyncClient) -> None:
    paths = (await client.get("/openapi.json")).json()["paths"]
    expected_prefixes = ["/v1/panchang", "/v1/festivals", "/v1/notes", "/v1/reminders",
                         "/v1/profile", "/v1/subscription", "/v1/pdf"]
    for prefix in expected_prefixes:
        matching = [p for p in paths if p.startswith(prefix)]
        assert matching, f"No paths found with prefix {prefix}"
