"""Focused S2 checks for durable overlays, receipt idempotency, and month assembly."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
from httpx import AsyncClient
from test_panchang import SAMPLE_PANCHANG

from api.auth import create_token
from api.models.auth import SubscriptionTier


def _auth(
    tier: SubscriptionTier = SubscriptionTier.SILVER, *, sub: str = "s2-user-unique"
) -> dict[str, str]:
    token = create_token(sub=sub, tier=tier)
    return {"Authorization": f"Bearer {token}"}


async def test_notes_bookmarks_and_reminders_round_trip(client: AsyncClient) -> None:
    headers = _auth()
    note = await client.post(
        "/v1/notes",
        json={"date": "2025-01-14", "body": "Temple visit", "tags": ["puja"]},
        headers=headers,
    )
    assert note.status_code == 201
    note_id = note.json()["data"]["id"]
    assert (await client.get("/v1/notes", headers=headers)).json()["data"][0]["id"] == note_id

    bookmark = await client.post(
        "/v1/bookmarks",
        json={"target_type": "festival", "target_id": "festival-1", "category": "favorites"},
        headers=headers,
    )
    assert bookmark.status_code == 201
    assert (await client.get("/v1/bookmarks", headers=headers)).json()["data"][0][
        "target_id"
    ] == "festival-1"

    reminder = await client.post(
        "/v1/reminders",
        json={
            "title": "Light diya",
            "trigger_type": "gregorian",
            "trigger_value": "2025-01-14T08:00:00+05:30",
            "advance_minutes": 15,
        },
        headers=headers,
    )
    assert reminder.status_code == 201
    assert reminder.json()["data"]["next_fire_at"].startswith("2025-01-14T02:15:00")

    invalid = await client.post(
        "/v1/reminders",
        json={
            "title": "Bad date",
            "trigger_type": "gregorian",
            "trigger_value": "not-a-date",
        },
        headers=headers,
    )
    assert invalid.status_code == 422

    unsupported_lunar = await client.post(
        "/v1/reminders",
        json={
            "title": "Ekadashi",
            "trigger_type": "tithi",
            "trigger_value": "11",
        },
        headers=headers,
    )
    assert unsupported_lunar.status_code == 422


async def test_profile_and_locations_round_trip(client: AsyncClient) -> None:
    headers = _auth(sub="profile-user-unique")
    initial = await client.get("/v1/profile", headers=headers)
    assert initial.status_code == 200
    assert initial.json()["data"]["default_month_scheme"] == "amanta"

    updated = await client.put(
        "/v1/profile",
        json={"display_name": "Asha", "default_month_scheme": "purnimanta"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["display_name"] == "Asha"
    assert updated.json()["data"]["default_month_scheme"] == "purnimanta"

    first = await client.post(
        "/v1/profile/locations",
        json={
            "name": "Delhi",
            "lat": 28.6139,
            "lon": 77.2090,
            "tz": "Asia/Kolkata",
            "is_default": True,
        },
        headers=headers,
    )
    second = await client.post(
        "/v1/profile/locations",
        json={
            "name": "Dubai",
            "lat": 25.2048,
            "lon": 55.2708,
            "tz": "Asia/Dubai",
            "is_default": True,
        },
        headers=headers,
    )
    assert first.status_code == 201
    assert second.status_code == 201
    locations = (await client.get("/v1/profile/locations", headers=headers)).json()["data"]
    assert [location["name"] for location in locations] == ["Dubai", "Delhi"]
    assert [location["is_default"] for location in locations] == [True, False]


async def test_birth_details_use_an_opaque_vault_reference(client: AsyncClient) -> None:
    headers = _auth(sub="birth-user-unique")
    body = {
        "dateOfBirth": "1990-02-03",
        "timeOfBirth": "04:05",
        "placeOfBirth": {"lat": 25.2, "lon": 55.3, "tz": "Asia/Dubai"},
    }
    saved = await client.put("/v1/profile/birth-details", json=body, headers=headers)
    assert saved.status_code == 200
    assert saved.json()["data"]["id"]
    assert "dateOfBirth" not in saved.text
    assert "placeOfBirth" not in saved.text

    reference = await client.get("/v1/profile/birth-details", headers=headers)
    assert reference.status_code == 200
    assert reference.json()["data"]["id"] == saved.json()["data"]["id"]

    exported = await client.get("/v1/profile/birth-details/export", headers=headers)
    assert exported.status_code == 200
    assert exported.json()["data"] == body

    other = await client.get(
        "/v1/profile/birth-details/export", headers=_auth(sub="other-birth-user")
    )
    assert other.status_code == 404

    deleted = await client.delete("/v1/profile/birth-details", headers=headers)
    assert deleted.status_code == 204
    assert (await client.get("/v1/profile/birth-details", headers=headers)).status_code == 404


async def test_receipt_reconciliation_is_idempotent_and_drives_entitlement(
    client: AsyncClient,
) -> None:
    headers = _auth(SubscriptionTier.BASIC)
    payload = {
        "provider": "test-adapter",
        "external_event_id": "evt-1",
        "provider_ref": "sub-1",
        "tier": "gold",
        "status": "active",
    }
    adapter_headers = {**headers, "X-Provider-Adapter-Token": "test-provider-token"}
    first = await client.post("/v1/subscription/receipts", json=payload, headers=adapter_headers)
    second = await client.post(
        "/v1/subscription/verify-receipt", json=payload, headers=adapter_headers
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["data"]["duplicate"] is True
    current = await client.get("/v1/subscription", headers=headers)
    assert current.json()["data"]["tier"] == "gold"

    changed = await client.post(
        "/v1/subscription/receipts",
        json={**payload, "tier": "silver"},
        headers=adapter_headers,
    )
    assert changed.status_code == 409

    other_owner = await client.post(
        "/v1/subscription/receipts",
        json={**payload, "external_event_id": "evt-2"},
        headers={
            **_auth(sub="another-s2-user"),
            "X-Provider-Adapter-Token": "test-provider-token",
        },
    )
    assert other_owner.status_code == 409

    client_attempt = await client.post("/v1/subscription/receipts", json=payload, headers=headers)
    assert client_attempt.status_code == 401


async def test_month_assembly_reports_missing_days(client: AsyncClient, silver_token: str) -> None:
    async def fetch(*, date: str, **_: object):
        if date == "2025-01-02":
            request = httpx.Request("GET", "http://pcs")
            response = httpx.Response(503, request=request)
            raise httpx.HTTPStatusError("unavailable", request=request, response=response)
        return SAMPLE_PANCHANG.model_copy(update={"date": date})

    with patch("api.routers.v1.panchang.fetch_daily_panchang", new=AsyncMock(side_effect=fetch)):
        response = await client.get(
            "/v1/panchang/month?year=2025&month=1&lat=28.6&lon=77.2&tz=Asia/Kolkata",
            headers={"Authorization": f"Bearer {silver_token}"},
        )
    assert response.status_code == 200
    assert response.json()["data"]["partial"] is True
    assert response.json()["data"]["missing_dates"] == ["2025-01-02"]
    assert response.headers["x-calendar-partial"] == "true"
