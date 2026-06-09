"""Tests: rate limiting trips at the configured threshold."""

from __future__ import annotations

from httpx import AsyncClient

from api.settings import get_settings


async def test_rate_limit_trips(client: AsyncClient, basic_token: str) -> None:
    """Sending more requests than the limit within a window returns 429."""
    settings = get_settings()
    limit = settings.rate_limit_per_minute

    headers = {"Authorization": f"Bearer {basic_token}"}
    url = "/v1/subscription"

    status_codes = []
    # Send limit + 5 requests
    for _ in range(limit + 5):
        r = await client.get(url, headers=headers)
        status_codes.append(r.status_code)

    assert 429 in status_codes, "Expected at least one 429 after exceeding rate limit"

    # The 429 response must include rate-limit headers
    # Re-fetch to inspect headers
    for _ in range(5):
        r = await client.get(url, headers=headers)
        if r.status_code == 429:
            assert "Retry-After" in r.headers
            assert "X-RateLimit-Limit" in r.headers
            assert "X-RateLimit-Remaining" in r.headers
            break


async def test_rate_limit_headers_present_on_ok(client: AsyncClient, basic_token: str) -> None:
    """Successful responses carry X-RateLimit-* headers."""
    r = await client.get(
        "/v1/subscription",
        headers={"Authorization": f"Bearer {basic_token}"},
    )
    assert r.status_code == 200
    assert "X-RateLimit-Limit" in r.headers
    assert "X-RateLimit-Remaining" in r.headers
