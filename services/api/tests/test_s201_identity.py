"""S2-01 persistence, ownership, Vault, and lifecycle contract tests."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.auth import create_token
from api.db import Base, get_session
from api.db.v3_models import OutboxEventRow, UserJobRow, UserRow, VaultRefRow
from api.main import app
from api.models.auth import SubscriptionTier


@pytest_asyncio.fixture
async def s201_client() -> AsyncIterator[tuple[AsyncClient, async_sessionmaker[AsyncSession]]]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with sessions() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, sessions
    app.dependency_overrides.pop(get_session, None)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def _auth(subject: str, tier: SubscriptionTier = SubscriptionTier.BASIC) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_token(subject, tier=tier)}"}


async def test_profile_and_location_persist_with_tier_limit(
    s201_client: tuple[AsyncClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, _ = s201_client
    headers = _auth("identity-a")

    initial = await client.get("/v1/me", headers=headers)
    assert initial.status_code == 200
    assert initial.json()["data"]["roles"] == ["patron"]
    assert initial.json()["data"]["has_birth_details"] is False

    updated = await client.put(
        "/v1/profile",
        headers=headers,
        json={
            "display_name": "Asha",
            "default_ayanamsa": "lahiri",
            "default_month_scheme": "purnimanta",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["display_name"] == "Asha"
    assert updated.json()["data"]["default_month_scheme"] == "purnimanta"

    partial = await client.put("/v1/profile", headers=headers, json={"default_ayanamsa": "lahiri"})
    assert partial.status_code == 200
    assert partial.json()["data"]["display_name"] == "Asha"

    location = await client.post(
        "/v1/me/locations",
        headers=headers,
        json={"name": "Dubai", "lat": 25.2048, "lon": 55.2708, "tz": "Asia/Dubai"},
    )
    assert location.status_code == 201
    assert location.json()["data"]["is_default"] is True
    location_id = location.json()["data"]["id"]

    over_limit = await client.post(
        "/v1/me/locations",
        headers=headers,
        json={"name": "London", "lat": 51.5072, "lon": -0.1276, "tz": "Europe/London"},
    )
    assert over_limit.status_code == 403
    assert over_limit.json()["detail"]["code"] == "location_limit_reached"

    listed = await client.get("/v1/profile/locations", headers=headers)
    assert [item["id"] for item in listed.json()["data"]] == [location_id]


async def test_locations_are_scoped_and_validate_iana_timezone(
    s201_client: tuple[AsyncClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, _ = s201_client
    response = await client.post(
        "/v1/me/locations",
        headers=_auth("identity-b"),
        json={"name": "Invalid", "lat": 0, "lon": 0, "tz": "Not/AZone"},
    )
    assert response.status_code == 422

    first = await client.post(
        "/v1/me/locations",
        headers=_auth("identity-a"),
        json={"name": "Delhi", "lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata"},
    )
    assert first.status_code == 201
    other = await client.get("/v1/me/locations", headers=_auth("identity-b"))
    assert other.status_code == 200
    assert other.json()["data"] == []


async def test_birth_details_use_opaque_vault_reference_and_can_be_erased(
    s201_client: tuple[AsyncClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, sessions = s201_client
    headers = _auth("identity-vault")
    stored = await client.put(
        "/v1/me/vault/birth-details",
        headers=headers,
        json={
            "date_of_birth": "1990-01-02",
            "time_of_birth": "03:04",
            "place_of_birth": {
                "name": "Private place",
                "lat": 28.6,
                "lon": 77.2,
                "tz": "Asia/Kolkata",
            },
        },
    )
    assert stored.status_code == 204
    profile = await client.get("/v1/me", headers=headers)
    assert profile.json()["data"]["has_birth_details"] is True
    assert "Private place" not in profile.text

    async with sessions() as session:
        ref = (await session.execute(select(VaultRefRow))).scalar_one()
        assert ref.purpose == "birth_details"
        assert ref.provider_ref.startswith("mem-vault-")
        user = (await session.execute(select(UserRow))).scalar_one()
        assert user.id == ref.subject_id
        assert "1990-01-02" not in repr(ref)

    erased = await client.delete("/v1/me/vault/birth-details", headers=headers)
    assert erased.status_code == 204
    assert (await client.get("/v1/me", headers=headers)).json()["data"][
        "has_birth_details"
    ] is False


async def test_export_and_deletion_are_durable_and_replay_safe(
    s201_client: tuple[AsyncClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, sessions = s201_client
    headers = _auth("identity-lifecycle")
    export = await client.post("/v1/me/export", headers=headers)
    replay = await client.post("/v1/me/export", headers=headers)
    assert export.status_code == replay.status_code == 202
    assert export.json()["data"]["id"] == replay.json()["data"]["id"]

    deletion = await client.delete("/v1/me", headers=headers)
    replay_delete = await client.delete("/v1/me", headers=headers)
    assert deletion.status_code == replay_delete.status_code == 202
    assert deletion.json()["data"]["id"] == replay_delete.json()["data"]["id"]
    blocked = await client.get("/v1/me", headers=headers)
    assert blocked.status_code == 403

    async with sessions() as session:
        jobs = list((await session.execute(select(UserJobRow))).scalars().all())
        events = list((await session.execute(select(OutboxEventRow))).scalars().all())
        assert {job.kind for job in jobs} == {"export", "deletion"}
        assert {event.event_type for event in events} == {
            "user.export_requested",
            "user.deletion_requested",
        }
        assert all("identity-lifecycle" not in event.payload_ref for event in events)
