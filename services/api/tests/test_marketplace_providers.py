"""Tests for A1 — Provider registration & onboarding flow.

Covers the dev-plan A1 acceptance criteria:

* creating/registering a Pandit provider profile requires the ``pandit`` role
  (mirrors F3's ``require_role`` 403 shape);
* the onboarding state machine (DRAFT → SUBMITTED → APPROVED | REJECTED |
  CHANGES_REQUESTED) enforces legal transitions and rejects illegal ones with a
  clear 4xx;
* agreement/code-of-conduct/cancellation-policy acceptances are versioned and
  logged (who + when), end-to-end through the HTTP API;
* the discoverability predicate (``list_discoverable`` / ``is_discoverable``) —
  reused by B1/A2 — excludes any pandit that is not both APPROVED and VERIFIED.

All DB-touching tests run on the shared in-memory SQLite engine, following the
F2/F3 pattern (``tests/test_marketplace_schema.py`` / ``test_marketplace_identity_vault.py``).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.auth import create_token
from api.db import Base, get_async_engine
from api.db.marketplace_models import (
    ONBOARDING_TRANSITIONS,
    AgreementType,
    OnboardingState,
    PanditRow,
)
from api.marketplace.providers.repository import (
    AgreementAcceptanceRepository,
    PanditRepository,
    discoverable_predicate,
    is_discoverable,
)
from api.marketplace.providers.service import (
    IllegalTransitionError,
    MissingAgreementsError,
    ProviderAlreadyRegisteredError,
    ProviderOnboardingService,
)
from api.models.auth import Role

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
async def _marketplace_schema():
    """Create every marketplace table on the shared app async engine.

    The ``client`` fixture (conftest.py) points ``API_DATABASE_URL`` at a shared
    in-memory SQLite DB, but nothing creates its schema for HTTP-level tests — the
    F2/F3 test files that use ``client`` never touch a DB-backed router. A1's
    router is the first real consumer of ``get_session`` from an HTTP handler, so
    this fixture builds ``Base.metadata`` on that same engine before each test.
    """
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def _pandit_token(sub: str = "pandit-user-1") -> str:
    return create_token(sub, roles=[Role.PANDIT])


def _patron_token(sub: str = "patron-user-1") -> str:
    return create_token(sub, roles=[Role.PATRON])


# ── HTTP: registration requires the pandit role ────────────────────────────────


async def test_register_requires_pandit_role(client: AsyncClient) -> None:
    token = _patron_token()
    resp = await client.post(
        "/v1/marketplace/providers/register",
        json={"display_name": "Pandit Sharma"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body["detail"]["code"] == "insufficient_role"


async def test_register_requires_auth(client: AsyncClient) -> None:
    resp = await client.post("/v1/marketplace/providers/register", json={"display_name": "No Auth"})
    assert resp.status_code == 401


async def test_register_creates_draft_profile(client: AsyncClient) -> None:
    token = _pandit_token("pandit-reg-1")
    resp = await client.post(
        "/v1/marketplace/providers/register",
        json={"display_name": "Pandit Sharma", "languages": ["hi", "en"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["display_name"] == "Pandit Sharma"
    assert data["onboarding_state"] == "draft"
    assert data["verification_status"] == "unverified"
    assert data["user_id"] == "pandit-reg-1"


async def test_register_twice_for_same_user_conflicts(client: AsyncClient) -> None:
    token = _pandit_token("pandit-reg-2")
    headers = {"Authorization": f"Bearer {token}"}
    first = await client.post(
        "/v1/marketplace/providers/register", json={"display_name": "First"}, headers=headers
    )
    assert first.status_code == 201
    second = await client.post(
        "/v1/marketplace/providers/register", json={"display_name": "Second"}, headers=headers
    )
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "already_registered"


async def test_get_own_profile_requires_registration_first(client: AsyncClient) -> None:
    token = _pandit_token("pandit-unregistered")
    resp = await client.get(
        "/v1/marketplace/providers/me", headers={"Authorization": f"Bearer {token}"}
    )
    # A global 404 handler (api.main.not_found_handler) rewrites every 404 body into
    # the generic ApiErrorResponse envelope, so only the status code is asserted here
    # — the same convention every other 404 test in this suite follows (e.g.
    # test_festivals.py, test_pdf.py, test_temple.py).
    assert resp.status_code == 404


# ── HTTP: agreement acceptance is versioned + logged ───────────────────────────


async def test_agreement_acceptance_is_versioned_and_logged(client: AsyncClient) -> None:
    token = _pandit_token("pandit-agree-1")
    headers = {"Authorization": f"Bearer {token}"}
    await client.post(
        "/v1/marketplace/providers/register",
        json={"display_name": "Agreeable Pandit"},
        headers=headers,
    )

    resp = await client.post(
        "/v1/marketplace/providers/me/agreements",
        json={"agreement_type": "partner_agreement", "version": "v1.0"},
        headers=headers,
    )
    assert resp.status_code == 201
    accepted = resp.json()["data"]
    assert accepted["agreement_type"] == "partner_agreement"
    assert accepted["version"] == "v1.0"
    assert accepted["accepted_by"] == "pandit-agree-1"
    assert "accepted_at" in accepted

    # Re-accepting a newer version logs a second row rather than overwriting.
    resp2 = await client.post(
        "/v1/marketplace/providers/me/agreements",
        json={"agreement_type": "partner_agreement", "version": "v1.1"},
        headers=headers,
    )
    assert resp2.status_code == 201

    history = await client.get("/v1/marketplace/providers/me/agreements", headers=headers)
    assert history.status_code == 200
    rows = history.json()["data"]
    assert len(rows) == 2
    assert [r["version"] for r in rows] == ["v1.0", "v1.1"]


# ── HTTP: submit_for_review gate + state machine transitions ──────────────────


async def test_submit_for_review_blocked_without_all_agreements(client: AsyncClient) -> None:
    token = _pandit_token("pandit-submit-1")
    headers = {"Authorization": f"Bearer {token}"}
    await client.post(
        "/v1/marketplace/providers/register",
        json={"display_name": "Impatient Pandit"},
        headers=headers,
    )
    # Accept only one of the three required agreements.
    await client.post(
        "/v1/marketplace/providers/me/agreements",
        json={"agreement_type": "partner_agreement", "version": "v1"},
        headers=headers,
    )

    resp = await client.post("/v1/marketplace/providers/me/submit-for-review", headers=headers)
    assert resp.status_code == 400
    body = resp.json()["detail"]
    assert body["code"] == "missing_agreements"
    assert "code_of_conduct" in body["missing"]
    assert "cancellation_policy" in body["missing"]


async def test_submit_for_review_succeeds_with_all_agreements(client: AsyncClient) -> None:
    token = _pandit_token("pandit-submit-2")
    headers = {"Authorization": f"Bearer {token}"}
    await client.post(
        "/v1/marketplace/providers/register",
        json={"display_name": "Prepared Pandit"},
        headers=headers,
    )
    for agreement_type in ("partner_agreement", "code_of_conduct", "cancellation_policy"):
        r = await client.post(
            "/v1/marketplace/providers/me/agreements",
            json={"agreement_type": agreement_type, "version": "v1"},
            headers=headers,
        )
        assert r.status_code == 201

    resp = await client.post("/v1/marketplace/providers/me/submit-for-review", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["previous_state"] == "draft"
    assert data["onboarding_state"] == "submitted"

    # Re-submitting from SUBMITTED is an illegal transition (not a valid target
    # state at all via this endpoint's fixed DRAFT->SUBMITTED semantics) — but the
    # underlying rule to prove here is that submit-for-review only succeeds from
    # DRAFT; a second call must now fail since the pandit is no longer in DRAFT.
    resp2 = await client.post("/v1/marketplace/providers/me/submit-for-review", headers=headers)
    assert resp2.status_code == 409
    assert resp2.json()["detail"]["code"] == "illegal_transition"


# ── Service-level: full state machine, every legal + illegal edge ─────────────


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def onboarding_service(db_session):
    return ProviderOnboardingService(
        PanditRepository(db_session), AgreementAcceptanceRepository(db_session)
    )


async def _register(service: ProviderOnboardingService, user_id: str) -> PanditRow:
    return await service.register(user_id=user_id, display_name=f"Pandit {user_id}")


async def test_state_machine_legal_transitions_table() -> None:
    """Sanity-check the transition table itself matches the dev-plan A1 spec."""
    assert ONBOARDING_TRANSITIONS[OnboardingState.DRAFT] == frozenset({OnboardingState.SUBMITTED})
    assert ONBOARDING_TRANSITIONS[OnboardingState.SUBMITTED] == frozenset(
        {
            OnboardingState.APPROVED,
            OnboardingState.REJECTED,
            OnboardingState.CHANGES_REQUESTED,
        }
    )
    assert ONBOARDING_TRANSITIONS[OnboardingState.APPROVED] == frozenset()
    assert ONBOARDING_TRANSITIONS[OnboardingState.REJECTED] == frozenset()
    assert ONBOARDING_TRANSITIONS[OnboardingState.CHANGES_REQUESTED] == frozenset(
        {OnboardingState.DRAFT}
    )


async def test_transition_draft_to_submitted(onboarding_service) -> None:
    pandit = await _register(onboarding_service, "svc-user-1")
    updated = await onboarding_service.transition_onboarding_state(
        pandit_id=pandit.id, to_state=OnboardingState.SUBMITTED
    )
    assert updated.onboarding_state == OnboardingState.SUBMITTED.value


@pytest.mark.parametrize(
    "target",
    [OnboardingState.APPROVED, OnboardingState.REJECTED, OnboardingState.CHANGES_REQUESTED],
)
async def test_transition_submitted_to_terminal_or_changes_requested(
    onboarding_service, target
) -> None:
    pandit = await _register(onboarding_service, f"svc-user-{target.value}")
    await onboarding_service.transition_onboarding_state(
        pandit_id=pandit.id, to_state=OnboardingState.SUBMITTED
    )
    updated = await onboarding_service.transition_onboarding_state(
        pandit_id=pandit.id, to_state=target
    )
    assert updated.onboarding_state == target.value


async def test_transition_changes_requested_back_to_draft(onboarding_service) -> None:
    pandit = await _register(onboarding_service, "svc-user-loop")
    await onboarding_service.transition_onboarding_state(
        pandit_id=pandit.id, to_state=OnboardingState.SUBMITTED
    )
    await onboarding_service.transition_onboarding_state(
        pandit_id=pandit.id, to_state=OnboardingState.CHANGES_REQUESTED
    )
    updated = await onboarding_service.transition_onboarding_state(
        pandit_id=pandit.id, to_state=OnboardingState.DRAFT
    )
    assert updated.onboarding_state == OnboardingState.DRAFT.value


@pytest.mark.parametrize(
    ("start", "illegal_target"),
    [
        (OnboardingState.DRAFT, OnboardingState.APPROVED),
        (OnboardingState.DRAFT, OnboardingState.REJECTED),
        (OnboardingState.DRAFT, OnboardingState.CHANGES_REQUESTED),
        (OnboardingState.APPROVED, OnboardingState.SUBMITTED),
        (OnboardingState.APPROVED, OnboardingState.DRAFT),
        (OnboardingState.REJECTED, OnboardingState.SUBMITTED),
        (OnboardingState.REJECTED, OnboardingState.DRAFT),
    ],
)
async def test_illegal_transitions_rejected(onboarding_service, start, illegal_target) -> None:
    pandit = await _register(
        onboarding_service, f"svc-illegal-{start.value}-{illegal_target.value}"
    )
    # Drive the pandit to `start` via legal moves first.
    if start != OnboardingState.DRAFT:
        await onboarding_service.transition_onboarding_state(
            pandit_id=pandit.id, to_state=OnboardingState.SUBMITTED
        )
        if start != OnboardingState.SUBMITTED:
            await onboarding_service.transition_onboarding_state(
                pandit_id=pandit.id, to_state=start
            )

    with pytest.raises(IllegalTransitionError) as exc_info:
        await onboarding_service.transition_onboarding_state(
            pandit_id=pandit.id, to_state=illegal_target
        )
    assert exc_info.value.current == start
    assert exc_info.value.requested == illegal_target


async def test_register_conflict_raises_domain_error(onboarding_service) -> None:
    await _register(onboarding_service, "dup-user")
    with pytest.raises(ProviderAlreadyRegisteredError):
        await _register(onboarding_service, "dup-user")


async def test_submit_for_review_raises_missing_agreements(onboarding_service) -> None:
    pandit = await _register(onboarding_service, "svc-missing-agreements")
    with pytest.raises(MissingAgreementsError) as exc_info:
        await onboarding_service.submit_for_review(pandit_id=pandit.id)
    missing = {a.value for a in exc_info.value.missing}
    assert missing == {"partner_agreement", "code_of_conduct", "cancellation_policy"}


async def test_agreement_acceptance_logged_at_service_level(onboarding_service, db_session) -> None:
    pandit = await _register(onboarding_service, "svc-log-user")
    await onboarding_service.accept_agreement(
        pandit_id=pandit.id,
        agreement_type=AgreementType.CODE_OF_CONDUCT,
        version="v2",
        accepted_by="svc-log-user",
    )
    history = await AgreementAcceptanceRepository(db_session).list_for_pandit(pandit.id)
    assert len(history) == 1
    row = history[0]
    assert row.agreement_type == AgreementType.CODE_OF_CONDUCT.value
    assert row.version == "v2"
    assert row.accepted_by == "svc-log-user"
    assert row.accepted_at is not None


# ── Discoverability predicate — the hard gate B1/A2 will reuse ────────────────


def _make_pandit(
    id_: str,
    *,
    onboarding_state: OnboardingState,
    verification_status: str,
) -> PanditRow:
    now = datetime.now(UTC)
    return PanditRow(
        id=id_,
        user_id=f"user-{id_}",
        display_name=f"Pandit {id_}",
        languages=[],
        onboarding_state=onboarding_state.value,
        verification_status=verification_status,
        rating_count=0,
        created_at=now,
        updated_at=now,
    )


async def test_is_discoverable_requires_approved_and_verified() -> None:
    approved_verified = _make_pandit(
        "p1", onboarding_state=OnboardingState.APPROVED, verification_status="verified"
    )
    approved_unverified = _make_pandit(
        "p2", onboarding_state=OnboardingState.APPROVED, verification_status="unverified"
    )
    submitted_verified = _make_pandit(
        "p3", onboarding_state=OnboardingState.SUBMITTED, verification_status="verified"
    )
    draft_unverified = _make_pandit(
        "p4", onboarding_state=OnboardingState.DRAFT, verification_status="unverified"
    )

    assert is_discoverable(approved_verified) is True
    assert is_discoverable(approved_unverified) is False
    assert is_discoverable(submitted_verified) is False
    assert is_discoverable(draft_unverified) is False


async def test_list_discoverable_excludes_non_approved_or_non_verified(db_session) -> None:
    pandits = [
        _make_pandit(
            "d1", onboarding_state=OnboardingState.APPROVED, verification_status="verified"
        ),
        _make_pandit(
            "d2", onboarding_state=OnboardingState.APPROVED, verification_status="unverified"
        ),
        _make_pandit(
            "d3", onboarding_state=OnboardingState.APPROVED, verification_status="pending"
        ),
        _make_pandit(
            "d4", onboarding_state=OnboardingState.SUBMITTED, verification_status="verified"
        ),
        _make_pandit("d5", onboarding_state=OnboardingState.DRAFT, verification_status="verified"),
        _make_pandit(
            "d6", onboarding_state=OnboardingState.REJECTED, verification_status="verified"
        ),
        _make_pandit(
            "d7",
            onboarding_state=OnboardingState.CHANGES_REQUESTED,
            verification_status="verified",
        ),
    ]
    for p in pandits:
        db_session.add(p)
    await db_session.flush()

    repo = PanditRepository(db_session)
    discoverable = await repo.list_discoverable()
    ids = {p.id for p in discoverable}
    assert ids == {"d1"}


async def test_discoverable_predicate_is_a_reusable_sql_expression(db_session) -> None:
    """Prove the predicate composes into an arbitrary query (as B1/A2 will do),
    not just PanditRepository's own convenience method."""
    from sqlalchemy import select

    pandit = _make_pandit(
        "sql1", onboarding_state=OnboardingState.APPROVED, verification_status="verified"
    )
    not_discoverable = _make_pandit(
        "sql2", onboarding_state=OnboardingState.DRAFT, verification_status="unverified"
    )
    db_session.add_all([pandit, not_discoverable])
    await db_session.flush()

    stmt = select(PanditRow).where(discoverable_predicate())
    result = await db_session.execute(stmt)
    rows = result.scalars().all()
    assert {r.id for r in rows} == {"sql1"}
