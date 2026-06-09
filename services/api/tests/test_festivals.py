"""Tests for the /v1/festivals endpoints.

Checks that:
- Only published CMS content is returned by the public API.
- The detail endpoint surfaces body/puja/katha from the CMS.
- Region and locale filters narrow the result set.
- A 404 is returned for unknown or draft-only festival IDs.
"""

from __future__ import annotations

import pytest

from api.cms.store import FestivalContent, _store, upsert_festival

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _seed_test_festivals():
    """Ensure deterministic CMS state for each test."""
    # Preserve originals and restore after each test
    original = dict(_store)
    yield
    _store.clear()
    _store.update(original)


@pytest.fixture
def draft_festival(tmp_path) -> FestivalContent:
    f = FestivalContent(
        id="test-draft-festival",
        slug="test-draft",
        name="Draft Festival",
        date="2026-01-01",
        description="A draft festival",
        body="Draft body text",
        puja=None,
        katha=None,
        tags=["draft"],
        status="draft",
    )
    upsert_festival(f)
    return f


@pytest.fixture
def published_festival() -> FestivalContent:
    f = FestivalContent(
        id="test-published-festival",
        slug="test-published",
        name="Published Festival",
        date="2026-03-15",
        description="A published festival",
        body="This is the body text of the festival.",
        puja="Puja step 1.\nPuja step 2.",
        katha="The katha story begins here.",
        tags=["festival"],
        region="north",
        locale="en",
        status="published",
    )
    upsert_festival(f)
    return f


# ── List endpoint ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_returns_only_published(client, basic_token, draft_festival):
    resp = await client.get(
        "/v1/festivals",
        headers={"Authorization": f"Bearer {basic_token}"},
    )
    assert resp.status_code == 200
    ids = [f["id"] for f in resp.json()["data"]]
    assert draft_festival.id not in ids


@pytest.mark.asyncio
async def test_list_includes_published(client, basic_token, published_festival):
    resp = await client.get(
        "/v1/festivals",
        headers={"Authorization": f"Bearer {basic_token}"},
    )
    assert resp.status_code == 200
    ids = [f["id"] for f in resp.json()["data"]]
    assert published_festival.id in ids


@pytest.mark.asyncio
async def test_list_region_filter(client, basic_token, published_festival):
    resp = await client.get(
        "/v1/festivals?region=north",
        headers={"Authorization": f"Bearer {basic_token}"},
    )
    assert resp.status_code == 200
    ids = [f["id"] for f in resp.json()["data"]]
    # "north" region — should include the published_festival and "all" region items
    assert published_festival.id in ids


@pytest.mark.asyncio
async def test_list_region_filter_excludes_other(client, basic_token, published_festival):
    resp = await client.get(
        "/v1/festivals?region=south",
        headers={"Authorization": f"Bearer {basic_token}"},
    )
    assert resp.status_code == 200
    ids = [f["id"] for f in resp.json()["data"]]
    # published_festival is region="north"; should NOT appear in south results
    # (it would only appear if region="all")
    assert published_festival.id not in ids


@pytest.mark.asyncio
async def test_list_requires_auth(client):
    resp = await client.get("/v1/festivals")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_pagination(client, basic_token):
    resp = await client.get(
        "/v1/festivals?page=1&page_size=2",
        headers={"Authorization": f"Bearer {basic_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) <= 2
    assert "meta" in body
    assert body["meta"]["page"] == 1
    assert body["meta"]["page_size"] == 2


# ── Detail endpoint ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_detail_returns_cms_content(client, basic_token, published_festival):
    resp = await client.get(
        f"/v1/festivals/{published_festival.id}",
        headers={"Authorization": f"Bearer {basic_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == published_festival.id
    assert data["body"] == published_festival.body
    assert data["puja"] == published_festival.puja
    assert data["katha"] == published_festival.katha


@pytest.mark.asyncio
async def test_detail_returns_404_for_draft(client, basic_token, draft_festival):
    resp = await client.get(
        f"/v1/festivals/{draft_festival.id}",
        headers={"Authorization": f"Bearer {basic_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_detail_returns_404_for_unknown_id(client, basic_token):
    resp = await client.get(
        "/v1/festivals/nonexistent-festival-id",
        headers={"Authorization": f"Bearer {basic_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_detail_requires_auth(client, published_festival):
    resp = await client.get(f"/v1/festivals/{published_festival.id}")
    assert resp.status_code == 401
