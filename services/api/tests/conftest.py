"""Shared fixtures for the API gateway test suite.

All tests use an in-process AsyncClient (no real network/Redis). The database is a
shared in-memory SQLite (set below before settings are read); temple tests create
and seed their tables via the store. The panchang downstream is mocked via httpx
transport overrides or direct cache injection so tests run fully offline.
"""

from __future__ import annotations

import os

# Point the DB at in-memory SQLite before anything reads settings. The engine
# factory applies a StaticPool so the in-memory DB is shared across connections.
os.environ.setdefault("API_DATABASE_URL", "sqlite://")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.auth import create_token
from api.cache import get_panchang_cache
from api.models.auth import SubscriptionTier


@pytest_asyncio.fixture
async def client():
    from api.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ── Pre-built tokens for common tiers ─────────────────────────────────────────


@pytest.fixture
def basic_token() -> str:
    return create_token(sub="user-basic-001", tier=SubscriptionTier.BASIC)


@pytest.fixture
def silver_token() -> str:
    return create_token(sub="user-silver-001", tier=SubscriptionTier.SILVER)


@pytest.fixture
def gold_token() -> str:
    return create_token(sub="user-gold-001", tier=SubscriptionTier.GOLD)


@pytest.fixture(autouse=True)
def clear_panchang_cache():
    """Reset the in-process LRU cache between tests."""
    get_panchang_cache().clear()
    yield
    get_panchang_cache().clear()


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Clear the in-process rate limiter state between tests."""
    # Walk the ASGI middleware chain to find the SlidingWindowRateLimiter
    from api.main import app
    from api.middleware.rate_limit import SlidingWindowRateLimiter

    node = getattr(app, "middleware_stack", None)
    while node is not None:
        if isinstance(node, SlidingWindowRateLimiter):
            node._windows.clear()
            break
        node = getattr(node, "app", None)
    yield
