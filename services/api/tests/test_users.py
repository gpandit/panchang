"""Tests for the Users, Auth & Profiles module (Step 2.1).

Exercises `UserService` directly against an in-memory SQLite database —
no HTTP layer needed to assert the business rules.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.users.db import init_models, make_engine, make_session_factory
from api.users.encryption import VaultCipher
from api.users.models import AuthProvider, Location, User
from api.users.oauth import ExternalIdentity, StaticVerifier
from api.users.security import RefreshError, decode_access_token, rotate_refresh_token
from api.users.service import AuthError, NotFoundError, UserService
from api.users.vault import (
    ANALYTICS_EXCLUDED_TABLES,
    BirthProfile,
    FamilyMember,
    Vault,
    VaultAccessLog,
)

SECRET_KEY = "test-secret-key-at-least-32-bytes-long"
TEST_KEY = VaultCipher.generate_key()


@pytest.fixture
async def session_factory() -> async_sessionmaker[AsyncSession]:
    engine = make_engine("sqlite+aiosqlite://")
    await init_models(engine)
    return make_session_factory("sqlite+aiosqlite://").__class__(engine, expire_on_commit=False)


@pytest.fixture
async def session(session_factory) -> AsyncSession:
    async with session_factory() as s:
        yield s


def _service(session: AsyncSession, **kwargs) -> UserService:
    vault = kwargs.pop("vault", None) or Vault(VaultCipher(TEST_KEY))
    verifiers = kwargs.pop("oauth_verifiers", None)
    return UserService(session, secret_key=SECRET_KEY, vault=vault, oauth_verifiers=verifiers)


# ──────────────────────────────────────────────────────────────────────────
# Sign-up: password, OAuth, guest
# ──────────────────────────────────────────────────────────────────────────


async def test_signup_with_password(session: AsyncSession) -> None:
    svc = _service(session)
    result = await svc.sign_up_with_password(
        email="dev@example.com", phone=None, password="hunter2", display_name="Dev"
    )
    await session.commit()

    assert result.user.email == "dev@example.com"
    assert result.user.password_hash != "hunter2"  # never stored in the clear
    assert decode_access_token(result.tokens.access_token, secret_key=SECRET_KEY) == result.user.id


async def test_signup_with_password_rejects_duplicate_identity(session: AsyncSession) -> None:
    svc = _service(session)
    await svc.sign_up_with_password(
        email="dup@example.com", phone=None, password="pw1", display_name=None
    )
    await session.flush()

    with pytest.raises(AuthError):
        await svc.sign_up_with_password(
            email="dup@example.com", phone=None, password="pw2", display_name=None
        )


async def test_signin_with_password_validates_credentials(session: AsyncSession) -> None:
    svc = _service(session)
    await svc.sign_up_with_password(
        email="login@example.com", phone=None, password="correct-horse", display_name=None
    )
    await session.commit()

    ok = await svc.sign_in_with_password(
        email="login@example.com", phone=None, password="correct-horse"
    )
    assert ok.user.email == "login@example.com"

    with pytest.raises(AuthError):
        await svc.sign_in_with_password(email="login@example.com", phone=None, password="wrong")


async def test_signup_guest_mode(session: AsyncSession) -> None:
    svc = _service(session)
    result = await svc.sign_up_guest()
    await session.commit()

    assert result.user.is_guest is True
    assert result.user.auth_provider == AuthProvider.GUEST.value
    assert result.user.email is None


async def test_signup_with_google_oauth(session: AsyncSession) -> None:
    verifier = StaticVerifier(
        {"good-google-token": ExternalIdentity(subject="g-123", email="g@example.com")}
    )
    svc = _service(session, oauth_verifiers={AuthProvider.GOOGLE: verifier})

    result = await svc.sign_up_or_sign_in_with_oauth(
        provider=AuthProvider.GOOGLE, identity_token="good-google-token", display_name="Googler"
    )
    await session.commit()

    assert result.user.auth_provider == AuthProvider.GOOGLE.value
    assert result.user.provider_subject == "g-123"
    assert result.user.email == "g@example.com"

    # Second sign-in with the same identity returns the same user, not a new one.
    again = await svc.sign_up_or_sign_in_with_oauth(
        provider=AuthProvider.GOOGLE, identity_token="good-google-token", display_name="Googler"
    )
    assert again.user.id == result.user.id


async def test_signup_with_apple_oauth(session: AsyncSession) -> None:
    verifier = StaticVerifier({"good-apple-token": ExternalIdentity(subject="a-456", email=None)})
    svc = _service(session, oauth_verifiers={AuthProvider.APPLE: verifier})

    result = await svc.sign_up_or_sign_in_with_oauth(
        provider=AuthProvider.APPLE, identity_token="good-apple-token", display_name=None
    )
    assert result.user.auth_provider == AuthProvider.APPLE.value
    assert result.user.provider_subject == "a-456"


async def test_oauth_rejects_invalid_token(session: AsyncSession) -> None:
    verifier = StaticVerifier({})
    svc = _service(session, oauth_verifiers={AuthProvider.GOOGLE: verifier})

    with pytest.raises(AuthError):
        await svc.sign_up_or_sign_in_with_oauth(
            provider=AuthProvider.GOOGLE, identity_token="bogus", display_name=None
        )


# ──────────────────────────────────────────────────────────────────────────
# Refresh-token rotation
# ──────────────────────────────────────────────────────────────────────────


async def test_refresh_token_rotates_and_old_token_becomes_invalid(session: AsyncSession) -> None:
    svc = _service(session)
    result = await svc.sign_up_guest()
    await session.commit()

    original_refresh = result.tokens.refresh_token
    rotated = await svc.refresh(raw_refresh_token=original_refresh)
    await session.commit()

    assert rotated.refresh_token != original_refresh
    assert decode_access_token(rotated.access_token, secret_key=SECRET_KEY) == result.user.id

    # Reusing the rotated-away token is rejected (and revokes the chain).
    with pytest.raises(AuthError):
        await svc.refresh(raw_refresh_token=original_refresh)

    # The token issued by the *reuse* attempt's revocation must also be dead —
    # i.e. the freshly rotated token from the legitimate call is now revoked too.
    with pytest.raises(AuthError):
        await svc.refresh(raw_refresh_token=rotated.refresh_token)


async def test_unknown_refresh_token_rejected(session: AsyncSession) -> None:
    with pytest.raises(RefreshError):
        await rotate_refresh_token(
            session, raw_refresh_token="not-a-real-token", secret_key=SECRET_KEY
        )


# ──────────────────────────────────────────────────────────────────────────
# Preferences CRUD
# ──────────────────────────────────────────────────────────────────────────


async def test_update_preferences(session: AsyncSession) -> None:
    svc = _service(session)
    result = await svc.sign_up_guest()
    await session.flush()

    updated = await svc.update_preferences(
        result.user.id,
        display_name="New Name",
        preferred_calendar_system="purnimanta",
        time_form="24h_plus",
        ayanamsa_override="raman",
        notification_settings={"festival_reminders": True},
    )

    assert updated.display_name == "New Name"
    assert updated.preferred_calendar_system == "purnimanta"
    assert updated.time_form == "24h_plus"
    assert updated.ayanamsa_override == "raman"
    assert updated.notification_settings == {"festival_reminders": True}


# ──────────────────────────────────────────────────────────────────────────
# Locations CRUD
# ──────────────────────────────────────────────────────────────────────────


async def test_location_crud(session: AsyncSession) -> None:
    svc = _service(session)
    result = await svc.sign_up_guest()
    await session.flush()
    uid = result.user.id

    created = await svc.add_location(
        uid,
        label="Home — Delhi",
        lat=28.6139,
        lon=77.2090,
        tz="Asia/Kolkata",
        dst_rule="iana",
        is_favourite=True,
        is_travel_mode=False,
    )
    assert created.label == "Home — Delhi"

    locations = await svc.list_locations(uid)
    assert len(locations) == 1

    updated = await svc.update_location(uid, created.id, is_travel_mode=True, label="Travelling")
    assert updated.is_travel_mode is True
    assert updated.label == "Travelling"

    await svc.delete_location(uid, created.id)
    assert await svc.list_locations(uid) == []


async def test_location_operations_are_owner_scoped(session: AsyncSession) -> None:
    svc = _service(session)
    owner = await svc.sign_up_guest()
    intruder = await svc.sign_up_guest()
    await session.flush()

    loc = await svc.add_location(
        owner.user.id,
        label="Mine",
        lat=1.0,
        lon=1.0,
        tz="Asia/Kolkata",
        dst_rule="iana",
        is_favourite=False,
        is_travel_mode=False,
    )

    with pytest.raises(NotFoundError):
        await svc.update_location(intruder.user.id, loc.id, label="Hijacked")

    with pytest.raises(NotFoundError):
        await svc.delete_location(intruder.user.id, loc.id)


# ──────────────────────────────────────────────────────────────────────────
# Vault: encryption at rest, access logging, analytics exclusion
# ──────────────────────────────────────────────────────────────────────────


async def test_vault_birth_profile_is_encrypted_at_rest(session: AsyncSession) -> None:
    svc = _service(session)
    result = await svc.sign_up_guest()
    await session.flush()
    uid = result.user.id

    sensitive = {"date": "1990-05-04", "time": "06:15", "place": "Ahmedabad", "nakshatra": "Rohini"}
    await svc.set_birth_profile(uid, sensitive)
    await session.flush()

    # Raw row must not contain any plaintext sensitive value.
    row = (
        await session.execute(select(BirthProfile).where(BirthProfile.user_id == uid))
    ).scalar_one()
    raw = row.encrypted_data
    assert b"Ahmedabad" not in raw
    assert b"Rohini" not in raw
    assert b"1990-05-04" not in raw

    # But the service round-trips it correctly via the cipher.
    fetched = await svc.get_birth_profile(uid)
    assert fetched == sensitive


async def test_vault_family_member_is_encrypted_at_rest(session: AsyncSession) -> None:
    svc = _service(session)
    result = await svc.sign_up_guest()
    await session.flush()
    uid = result.user.id

    await svc.add_family_member(uid, "Mother", {"birth_nakshatra": "Ashwini", "gotra": "Kashyapa"})
    await session.flush()

    row = (
        await session.execute(select(FamilyMember).where(FamilyMember.user_id == uid))
    ).scalar_one()
    assert b"Ashwini" not in row.encrypted_data
    assert b"Kashyapa" not in row.encrypted_data

    members = await svc.list_family_members(uid)
    assert len(members) == 1
    assert members[0]["birth_nakshatra"] == "Ashwini"
    assert members[0]["relation"] == "Mother"


async def test_vault_access_is_logged(session: AsyncSession) -> None:
    svc = _service(session)
    result = await svc.sign_up_guest()
    await session.flush()
    uid = result.user.id

    await svc.set_birth_profile(uid, {"date": "1990-05-04"})
    await svc.get_birth_profile(uid)
    await svc.add_family_member(uid, "Father", {"gotra": "Bharadwaja"})
    await svc.list_family_members(uid)
    await session.flush()

    log = (
        (await session.execute(select(VaultAccessLog).where(VaultAccessLog.user_id == uid)))
        .scalars()
        .all()
    )
    actions = [(entry.action, entry.target_type) for entry in log]

    assert ("create", "birth_profile") in actions
    assert ("read", "birth_profile") in actions
    assert ("create", "family_member") in actions
    assert ("read", "family_member") in actions
    assert all(entry.actor_id == uid for entry in log)


def test_vault_tables_excluded_from_analytics() -> None:
    """The analytics pipeline's authoritative exclusion list must cover
    every vault table — this is the contract analytics jobs assert against."""
    assert "vault_birth_profiles" in ANALYTICS_EXCLUDED_TABLES
    assert "vault_family_members" in ANALYTICS_EXCLUDED_TABLES
    assert "vault_access_log" in ANALYTICS_EXCLUDED_TABLES
    # And nothing from the general user-profile surface leaks in here.
    assert "users" not in ANALYTICS_EXCLUDED_TABLES
    assert "locations" not in ANALYTICS_EXCLUDED_TABLES


async def test_user_row_never_carries_birth_fields(session: AsyncSession) -> None:
    """Defence-in-depth: assert the User ORM model has no birth/family columns."""
    column_names = {c.name for c in User.__table__.columns}
    forbidden = {"birth_date", "birth_time", "birth_place", "gotra", "nakshatra", "birth_nakshatra"}
    assert column_names.isdisjoint(forbidden)


# ──────────────────────────────────────────────────────────────────────────
# Account lifecycle: deletion & export
# ──────────────────────────────────────────────────────────────────────────


async def test_account_deletion_removes_user_and_vault_data(session: AsyncSession) -> None:
    svc = _service(session)
    result = await svc.sign_up_with_password(
        email="bye@example.com", phone=None, password="pw", display_name="Bye"
    )
    await session.flush()
    uid = result.user.id

    await svc.add_location(
        uid,
        label="Home",
        lat=1.0,
        lon=1.0,
        tz="Asia/Kolkata",
        dst_rule="iana",
        is_favourite=False,
        is_travel_mode=False,
    )
    await svc.set_birth_profile(uid, {"date": "1990-01-01"})
    await svc.add_family_member(uid, "Sister", {"gotra": "Vashishta"})
    await session.flush()

    await svc.delete_account(uid)
    await session.commit()

    assert (await session.get(User, uid)) is None
    assert (
        await session.execute(select(Location).where(Location.user_id == uid))
    ).scalars().all() == []
    assert (
        await session.execute(select(BirthProfile).where(BirthProfile.user_id == uid))
    ).scalar_one_or_none() is None
    assert (
        await session.execute(select(FamilyMember).where(FamilyMember.user_id == uid))
    ).scalars().all() == []

    with pytest.raises(NotFoundError):
        await svc.get_user(uid)


async def test_account_deletion_is_audited(session: AsyncSession) -> None:
    from api.users.models import AccountAuditLog

    svc = _service(session)
    result = await svc.sign_up_guest()
    await session.flush()
    uid = result.user.id

    await svc.delete_account(uid)
    await session.commit()

    entries = (
        (await session.execute(select(AccountAuditLog).where(AccountAuditLog.user_id == uid)))
        .scalars()
        .all()
    )
    assert any(e.action == "account_deleted" for e in entries)


async def test_data_export_produces_complete_archive(session: AsyncSession) -> None:
    svc = _service(session)
    result = await svc.sign_up_with_password(
        email="export@example.com", phone=None, password="pw", display_name="Ex"
    )
    await session.flush()
    uid = result.user.id

    await svc.add_location(
        uid,
        label="Office",
        lat=2.0,
        lon=2.0,
        tz="Asia/Dubai",
        dst_rule="iana",
        is_favourite=True,
        is_travel_mode=False,
    )
    await svc.set_birth_profile(uid, {"date": "1985-09-09", "place": "Dubai"})
    await svc.add_family_member(uid, "Brother", {"gotra": "Atri"})
    await session.flush()

    archive = await svc.export_data(uid)

    assert archive["profile"]["id"] == uid
    assert archive["profile"]["email"] == "export@example.com"
    assert len(archive["locations"]) == 1
    assert archive["locations"][0]["label"] == "Office"
    assert archive["vault"]["birth_profile"] == {"date": "1985-09-09", "place": "Dubai"}
    assert archive["vault"]["family_members"][0]["gotra"] == "Atri"

    from api.users.models import AccountAuditLog

    entries = (
        (await session.execute(select(AccountAuditLog).where(AccountAuditLog.user_id == uid)))
        .scalars()
        .all()
    )
    assert any(e.action == "data_exported" for e in entries)


async def test_export_and_then_delete_leaves_nothing_behind(session: AsyncSession) -> None:
    svc = _service(session)
    result = await svc.sign_up_guest()
    await session.flush()
    uid = result.user.id

    await svc.set_birth_profile(uid, {"date": "2000-01-01"})
    archive = await svc.export_data(uid)
    assert archive["vault"]["birth_profile"] is not None

    await svc.delete_account(uid)
    await session.commit()

    assert (await session.execute(select(BirthProfile))).scalars().all() == []
