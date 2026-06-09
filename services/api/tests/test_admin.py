"""Tests for admin console — RBAC, content workflow, flag queue, reporting."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.admin import audit as audit_log
from api.admin import content_store, flags_store
from api.auth import create_admin_token, create_token
from api.models.auth import SubscriptionTier

# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def client():
    from api.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture(autouse=True)
def clean_stores():
    content_store.clear()
    flags_store.clear()
    audit_log.clear()
    yield
    content_store.clear()
    flags_store.clear()
    audit_log.clear()


@pytest.fixture
def viewer_token():
    return create_admin_token("admin-viewer", "viewer")


@pytest.fixture
def editor_token():
    return create_admin_token("admin-editor", "editor")


@pytest.fixture
def publisher_token():
    return create_admin_token("admin-publisher", "publisher")


@pytest.fixture
def super_token():
    return create_admin_token("admin-super", "super_admin")


@pytest.fixture
def user_token():
    return create_token("user-001", tier=SubscriptionTier.BASIC)


_FESTIVAL_PAYLOAD = {
    "name": "Test Pongal",
    "slug": "test-pongal",
    "date": "2026-01-14",
    "description": "Harvest festival.",
    "body": "Full body text.",
    "puja": "Puja instructions.",
    "katha": "Katha text.",
    "tags": ["harvest", "south"],
    "region": "south",
    "locale": "en",
}


# ── Role protection ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_viewer_cannot_create_festival(client, viewer_token):
    """VIEWER role must not be able to create content (requires EDITOR)."""
    resp = await client.post(
        "/admin/v1/content/festivals",
        json=_FESTIVAL_PAYLOAD,
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "insufficient_admin_role"


@pytest.mark.asyncio
async def test_non_admin_token_denied(client, user_token):
    """A regular (non-admin) token must not access admin endpoints."""
    resp = await client.get(
        "/admin/v1/content/festivals",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "not_admin"


@pytest.mark.asyncio
async def test_editor_cannot_publish(client, editor_token):
    """EDITOR may submit for review but not publish (requires PUBLISHER)."""
    # Create
    resp = await client.post(
        "/admin/v1/content/festivals",
        json=_FESTIVAL_PAYLOAD,
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert resp.status_code == 201
    fid = resp.json()["id"]

    # Submit for review (allowed)
    resp = await client.post(
        f"/admin/v1/content/festivals/{fid}/submit-review",
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert resp.status_code == 200

    # Publish (denied)
    resp = await client.post(
        f"/admin/v1/content/festivals/{fid}/publish",
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert resp.status_code == 403


# ── Content workflow ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_full_create_review_publish_workflow(
    client, editor_token, publisher_token, user_token
):
    """Create → submit for review → publish → appears in public API."""
    # Create (DRAFT)
    resp = await client.post(
        "/admin/v1/content/festivals",
        json=_FESTIVAL_PAYLOAD,
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    fid = data["id"]
    assert data["status"] == "draft"

    # Submit for review
    resp = await client.post(
        f"/admin/v1/content/festivals/{fid}/submit-review",
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "review"

    # Publish
    resp = await client.post(
        f"/admin/v1/content/festivals/{fid}/publish",
        headers={"Authorization": f"Bearer {publisher_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "published"

    # Appears in public API
    resp = await client.get(
        f"/v1/festivals/{fid}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "Test Pongal"


@pytest.mark.asyncio
async def test_version_history_grows_with_workflow(client, editor_token, publisher_token):
    resp = await client.post(
        "/admin/v1/content/festivals",
        json=_FESTIVAL_PAYLOAD,
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    fid = resp.json()["id"]

    await client.post(
        f"/admin/v1/content/festivals/{fid}/submit-review",
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    await client.post(
        f"/admin/v1/content/festivals/{fid}/publish",
        headers={"Authorization": f"Bearer {publisher_token}"},
    )

    resp = await client.get(
        f"/admin/v1/content/festivals/{fid}",
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    versions = resp.json()["versions"]
    assert len(versions) == 3  # create, review, publish


# ── Audit trail ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_authorised_action_is_logged(client, publisher_token, editor_token):
    resp = await client.post(
        "/admin/v1/content/festivals",
        json=_FESTIVAL_PAYLOAD,
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    fid = resp.json()["id"]

    await client.post(
        f"/admin/v1/content/festivals/{fid}/submit-review",
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    await client.post(
        f"/admin/v1/content/festivals/{fid}/publish",
        headers={"Authorization": f"Bearer {publisher_token}"},
    )

    resp = await client.get(
        "/admin/v1/content/audit",
        headers={"Authorization": f"Bearer {publisher_token}"},
    )
    assert resp.status_code == 200
    actions = [e["action"] for e in resp.json()]
    assert "content.create" in actions
    assert "content.review" in actions
    assert "content.published" in actions


# ── Flag / review queue ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_flagged_item_appears_in_review_queue(client, user_token, editor_token):
    # Any authenticated user can flag
    resp = await client.post(
        "/admin/v1/flags/report",
        json={
            "resource_type": "festival",
            "resource_id": "fest-diwali",
            "reason": "wrong_date",
            "details": "Date appears to be off by one day.",
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 201
    flag_id = resp.json()["id"]

    # Admin sees it in queue
    resp = await client.get(
        "/admin/v1/flags",
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert resp.status_code == 200
    ids = [f["id"] for f in resp.json()]
    assert flag_id in ids


@pytest.mark.asyncio
async def test_resolve_flag_updates_status_and_audit(client, user_token, editor_token):
    # Flag
    resp = await client.post(
        "/admin/v1/flags/report",
        json={
            "resource_type": "panchang_date",
            "resource_id": "2026-01-15",
            "reason": "incorrect_tithi",
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    flag_id = resp.json()["id"]

    # Resolve
    resp = await client.post(
        f"/admin/v1/flags/{flag_id}/resolve",
        json={"action": "resolve", "resolution_note": "Verified correct, closing."},
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"

    # Audit entry logged
    entries = audit_log.list_entries()
    actions = [e.action for e in entries]
    assert "flag.resolve" in actions


# ── Reporting ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reports_render_signups_active_conversions(client, viewer_token):
    resp = await client.get(
        "/admin/v1/reporting/overview?period=last_7d",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["period"] == "last_7d"
    assert len(data["rows"]) == 7
    for row in data["rows"]:
        assert "signups" in row
        assert "active_users" in row
        assert "conversions" in row
    totals = data["totals"]
    assert totals["signups"] == sum(r["signups"] for r in data["rows"])


@pytest.mark.asyncio
async def test_reports_require_admin_role(client, user_token):
    resp = await client.get(
        "/admin/v1/reporting/overview",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 403
