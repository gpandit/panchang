"""Tests for the temple-admin surface — login, config edit, public read, provisioning."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.auth import create_admin_token, create_token
from api.temple import store


@pytest_asyncio.fixture
async def client():
    from api.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture(autouse=True)
def clean_store():
    store.clear()
    store.seed()
    yield
    store.clear()
    store.seed()


@pytest.fixture
def super_token() -> str:
    return create_admin_token("admin-super", "super_admin")


async def _login(client: AsyncClient, email: str, password: str):
    return await client.post(
        "/temple/v1/auth/login", json={"email": email, "password": password}
    )


# ── Login ────────────────────────────────────────────────────────────────────


async def test_login_success_returns_token_and_temple(client: AsyncClient):
    resp = await _login(client, store.DEMO_ADMIN_EMAIL, store.DEMO_ADMIN_PASSWORD)
    assert resp.status_code == 200
    body = resp.json()
    assert body["temple_id"] == store.DEMO_TEMPLE_ID
    assert body["token"]


async def test_login_wrong_password_401(client: AsyncClient):
    resp = await _login(client, store.DEMO_ADMIN_EMAIL, "nope")
    assert resp.status_code == 401


async def test_login_unknown_email_401(client: AsyncClient):
    resp = await _login(client, "ghost@temple.test", "whatever")
    assert resp.status_code == 401


# ── me / config require a temple token ───────────────────────────────────────


async def test_me_requires_temple_token(client: AsyncClient):
    # A plain user token has no temple_id claim → 403.
    plain = create_token("user-1")
    resp = await client.get(
        "/temple/v1/auth/me", headers={"Authorization": f"Bearer {plain}"}
    )
    assert resp.status_code == 403


async def test_me_returns_assigned_temple(client: AsyncClient):
    login = await _login(client, store.DEMO_ADMIN_EMAIL, store.DEMO_ADMIN_PASSWORD)
    token = login.json()["token"]
    resp = await client.get(
        "/temple/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == store.DEMO_TEMPLE_ID


# ── Update config ────────────────────────────────────────────────────────────


async def test_update_persists_and_keeps_identity(client: AsyncClient):
    login = await _login(client, store.DEMO_ADMIN_EMAIL, store.DEMO_ADMIN_PASSWORD)
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "location": {
            "label": "Mumbai · India",
            "lat": 19.076,
            "lon": 72.8777,
            "tz": "Asia/Kolkata",
        },
        "aarti": [
            {"key": "mangala", "name": "Maṅgala", "dev": "मंगला", "time": "06:00", "note": "x"}
        ],
        "events": [
            {"id": "e1", "title": "Ekadashi", "date": "2026-06-20"}
        ],
    }
    resp = await client.put("/temple/v1/temple", json=payload, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["location"]["lat"] == 19.076
    assert len(body["aarti"]) == 1
    assert body["events"][0]["title"] == "Ekadashi"
    # Identity preserved (not in the editable payload).
    assert body["name"] == "Shree Siddhivinayak Mandir"

    # Re-read reflects the change.
    again = await client.get("/temple/v1/temple", headers=headers)
    assert again.json()["location"]["label"] == "Mumbai · India"


# ── Public read for the Display ──────────────────────────────────────────────


async def test_public_read_no_auth(client: AsyncClient):
    resp = await client.get(f"/v1/temple/{store.DEMO_TEMPLE_ID}")
    assert resp.status_code == 200
    assert resp.json()["name_dev"] == "श्री सिद्धिविनायक मंदिर"


async def test_public_read_unknown_404(client: AsyncClient):
    resp = await client.get("/v1/temple/does-not-exist")
    assert resp.status_code == 404


# ── Superuser provisioning ───────────────────────────────────────────────────


async def test_superuser_creates_temple_and_assigns_admin(
    client: AsyncClient, super_token: str
):
    headers = {"Authorization": f"Bearer {super_token}"}
    create = await client.post(
        "/admin/v1/temples",
        headers=headers,
        json={
            "name": "New Mandir",
            "name_dev": "नया मंदिर",
            "tagline": "",
            "location": {"label": "Pune", "lat": 18.52, "lon": 73.85, "tz": "Asia/Kolkata"},
            "aarti": [],
            "events": [],
        },
    )
    assert create.status_code == 201
    tid = create.json()["id"]

    assign = await client.post(
        f"/admin/v1/temples/{tid}/admins",
        headers=headers,
        json={"email": "newadmin@temple.test", "password": "secret123"},
    )
    assert assign.status_code == 201

    # The newly provisioned admin can log in and lands on the new temple.
    login = await _login(client, "newadmin@temple.test", "secret123")
    assert login.status_code == 200
    assert login.json()["temple_id"] == tid


async def test_non_superuser_cannot_create_temple(client: AsyncClient):
    editor = create_admin_token("admin-editor", "editor")
    resp = await client.post(
        "/admin/v1/temples",
        headers={"Authorization": f"Bearer {editor}"},
        json={
            "name": "X",
            "name_dev": "X",
            "location": {"label": "X", "lat": 0, "lon": 0, "tz": "UTC"},
        },
    )
    assert resp.status_code == 403
