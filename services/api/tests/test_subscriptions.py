"""Tests for the Subscriptions & Billing module (Step 2.6).

Tests SubscriptionService directly against an in-memory SQLite database.
Receipt verifiers are replaced with StaticReceiptVerifier — no network calls.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.subscriptions.entitlements import (
    EntitlementError,
    Feature,
    check_boolean,
    check_quantity,
    get_limits,
    is_allowed_boolean,
    is_allowed_quantity,
)
from api.subscriptions.models import (
    BillingSource,
    SubscriptionStatus,
    Tier,
)
from api.subscriptions.service import SubscriptionService
from api.subscriptions.verifiers import (
    StaticReceiptVerifier,
    VerificationError,
    VerifiedReceipt,
)
from api.users.db import Base, make_engine

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def session() -> AsyncSession:
    engine = make_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s


def _gold_receipt(expires_in_days: int = 30) -> VerifiedReceipt:
    return VerifiedReceipt(
        source=BillingSource.APPLE,
        tier=Tier.GOLD,
        provider_subscription_id="txn_gold_001",
        expires_at=datetime.now(UTC) + timedelta(days=expires_in_days),
        meta={"product_id": "com.pandit.gold.monthly", "environment": "Sandbox"},
    )


def _silver_receipt(source: BillingSource = BillingSource.GOOGLE) -> VerifiedReceipt:
    return VerifiedReceipt(
        source=source,
        tier=Tier.SILVER,
        provider_subscription_id="sub_silver_001",
        expires_at=datetime.now(UTC) + timedelta(days=30),
        meta={"product_id": "pandit_silver_monthly"},
    )


def _stripe_gold_receipt() -> VerifiedReceipt:
    return VerifiedReceipt(
        source=BillingSource.STRIPE,
        tier=Tier.GOLD,
        provider_subscription_id="sub_stripe_gold",
        expires_at=datetime.now(UTC) + timedelta(days=365),
        meta={"price_id": "price_gold_annual", "status": "active"},
    )


def _svc(session: AsyncSession, **verifier_overrides: StaticReceiptVerifier) -> SubscriptionService:
    verifiers = {
        BillingSource.APPLE: StaticReceiptVerifier(result=_gold_receipt()),
        BillingSource.GOOGLE: StaticReceiptVerifier(result=_silver_receipt()),
        BillingSource.STRIPE: StaticReceiptVerifier(result=_stripe_gold_receipt()),
    }
    verifiers.update(verifier_overrides)
    return SubscriptionService(session, verifiers)  # type: ignore[arg-type]


USER = "user-abc-123"


# ── Entitlement matrix ────────────────────────────────────────────────────────


def test_basic_limits() -> None:
    lim = get_limits(Tier.BASIC)
    assert lim.panchang_lookahead_days == 7
    assert lim.saved_locations == 1
    assert lim.pdf_exports_per_month == 0
    assert lim.muhurat_planning is False
    assert lim.ad_free is False


def test_silver_limits() -> None:
    lim = get_limits(Tier.SILVER)
    assert lim.panchang_lookahead_days == 90
    assert lim.saved_locations == 3
    assert lim.pdf_exports_per_month == 1
    assert lim.muhurat_planning is True


def test_gold_limits() -> None:
    lim = get_limits(Tier.GOLD)
    assert lim.saved_locations == -1  # unlimited
    assert lim.ai_queries_per_month == -1
    assert lim.priority_cache is True


# ── Entitlement check functions ───────────────────────────────────────────────


def test_check_boolean_passes_for_allowed_tier() -> None:
    check_boolean(Tier.SILVER, Feature.MUHURAT_PLANNING)  # should not raise


def test_check_boolean_raises_for_denied_tier() -> None:
    with pytest.raises(EntitlementError):
        check_boolean(Tier.BASIC, Feature.MUHURAT_PLANNING)


def test_check_quantity_passes_under_limit() -> None:
    check_quantity(Tier.SILVER, Feature.SAVED_LOCATIONS, current=2)  # limit=3


def test_check_quantity_raises_at_limit() -> None:
    with pytest.raises(EntitlementError):
        check_quantity(Tier.SILVER, Feature.SAVED_LOCATIONS, current=3)  # limit=3


def test_check_quantity_unlimited_never_raises() -> None:
    check_quantity(Tier.GOLD, Feature.SAVED_LOCATIONS, current=9999)


def test_is_allowed_helpers() -> None:
    assert is_allowed_boolean(Tier.GOLD, Feature.MUHURAT_PLANNING) is True
    assert is_allowed_boolean(Tier.BASIC, Feature.MUHURAT_PLANNING) is False
    assert is_allowed_quantity(Tier.SILVER, Feature.ACTIVE_REMINDERS, current=10) is True
    assert is_allowed_quantity(Tier.BASIC, Feature.PDF_EXPORTS_PER_MONTH, current=0) is False


# ── Apple IAP receipt → correct Subscription ─────────────────────────────────


async def test_apple_receipt_creates_gold_subscription(session: AsyncSession) -> None:
    svc = _svc(
        session,
        **{BillingSource.APPLE: StaticReceiptVerifier(result=_gold_receipt())},
    )
    sub = await svc.verify_and_upsert(USER, BillingSource.APPLE, "fake-apple-receipt")
    await session.commit()

    assert sub.tier == Tier.GOLD.value
    assert sub.source == BillingSource.APPLE.value
    assert sub.status == SubscriptionStatus.ACTIVE.value
    assert sub.provider_subscription_id == "txn_gold_001"
    assert sub.effective_tier == Tier.GOLD


# ── Google Play receipt → correct Subscription ───────────────────────────────


async def test_google_receipt_creates_silver_subscription(session: AsyncSession) -> None:
    svc = _svc(
        session,
        **{BillingSource.GOOGLE: StaticReceiptVerifier(result=_silver_receipt(BillingSource.GOOGLE))},
    )
    sub = await svc.verify_and_upsert(USER, BillingSource.GOOGLE, '{"productId":"x","purchaseToken":"y"}')
    await session.commit()

    assert sub.tier == Tier.SILVER.value
    assert sub.source == BillingSource.GOOGLE.value
    assert sub.effective_tier == Tier.SILVER


# ── Stripe receipt → correct Subscription ────────────────────────────────────


async def test_stripe_receipt_creates_gold_subscription(session: AsyncSession) -> None:
    svc = _svc(
        session,
        **{BillingSource.STRIPE: StaticReceiptVerifier(result=_stripe_gold_receipt())},
    )
    sub = await svc.verify_and_upsert(USER, BillingSource.STRIPE, "sub_stripe_gold")
    await session.commit()

    assert sub.tier == Tier.GOLD.value
    assert sub.source == BillingSource.STRIPE.value
    assert sub.effective_tier == Tier.GOLD


# ── Invalid receipt raises VerificationError ─────────────────────────────────


async def test_invalid_receipt_raises(session: AsyncSession) -> None:
    svc = _svc(
        session,
        **{BillingSource.APPLE: StaticReceiptVerifier(error="receipt tampered")},
    )
    with pytest.raises(VerificationError, match="receipt tampered"):
        await svc.verify_and_upsert(USER, BillingSource.APPLE, "bad-receipt")


# ── Upgrade: Silver → Gold changes entitlements ───────────────────────────────


async def test_upgrade_silver_to_gold(session: AsyncSession) -> None:
    svc = _svc(session)
    # Start on Silver
    await svc.verify_and_upsert(USER, BillingSource.GOOGLE, "receipt-a")
    await session.commit()
    assert await svc.get_effective_tier(USER) == Tier.SILVER

    # Upgrade to Gold
    svc2 = _svc(
        session,
        **{BillingSource.APPLE: StaticReceiptVerifier(result=_gold_receipt())},
    )
    await svc2.verify_and_upsert(USER, BillingSource.APPLE, "receipt-b")
    await session.commit()
    assert await svc2.get_effective_tier(USER) == Tier.GOLD


# ── Downgrade: Gold → Silver changes entitlements ────────────────────────────


async def test_downgrade_gold_to_silver(session: AsyncSession) -> None:
    svc = _svc(session)
    # Start on Gold
    await svc.verify_and_upsert(USER, BillingSource.APPLE, "receipt-gold")
    await session.commit()
    assert await svc.get_effective_tier(USER) == Tier.GOLD

    # Downgrade to Silver (e.g. user switched plan)
    silver = StaticReceiptVerifier(result=_silver_receipt(BillingSource.STRIPE))
    svc2 = _svc(session, **{BillingSource.STRIPE: silver})
    await svc2.verify_and_upsert(USER, BillingSource.STRIPE, "receipt-silver")
    await session.commit()
    assert await svc2.get_effective_tier(USER) == Tier.SILVER

    # Gold-only feature should now be denied
    await svc2.check_boolean_feature(USER, Feature.AD_FREE)  # Silver still has ad_free
    with pytest.raises(EntitlementError):
        # priority_cache is Gold-only
        await svc2.check_boolean_feature(USER, Feature.PRIORITY_CACHE)


# ── Entitlement check flips on tier change ───────────────────────────────────


async def test_gated_check_flips_on_upgrade(session: AsyncSession) -> None:
    svc = _svc(
        session,
        **{BillingSource.GOOGLE: StaticReceiptVerifier(result=_silver_receipt())},
    )
    await svc.verify_and_upsert(USER, BillingSource.GOOGLE, "receipt-silver")
    await session.commit()

    # PDF exports: Basic=0, Silver=1, Gold=unlimited
    # On Silver, current=0 is within limit (limit=1)
    await svc.check_quantity_feature(USER, Feature.PDF_EXPORTS_PER_MONTH, current=0)
    # At limit
    with pytest.raises(EntitlementError):
        await svc.check_quantity_feature(USER, Feature.PDF_EXPORTS_PER_MONTH, current=1)

    # Upgrade to Gold
    svc2 = _svc(session)
    await svc2.verify_and_upsert(USER, BillingSource.APPLE, "receipt-gold")
    await session.commit()
    # Now unlimited — should pass at any count
    await svc2.check_quantity_feature(USER, Feature.PDF_EXPORTS_PER_MONTH, current=999)


# ── Cancellation revokes entitlement ─────────────────────────────────────────


async def test_cancellation_reverts_to_basic(session: AsyncSession) -> None:
    svc = _svc(session)
    await svc.verify_and_upsert(USER, BillingSource.APPLE, "receipt-gold")
    await session.commit()
    assert await svc.get_effective_tier(USER) == Tier.GOLD

    sub = await svc.cancel(USER)
    await session.commit()

    assert sub.status == SubscriptionStatus.CANCELLED.value
    assert sub.effective_tier == Tier.BASIC
    assert await svc.get_effective_tier(USER) == Tier.BASIC

    # Gold-only feature now denied
    with pytest.raises(EntitlementError):
        await svc.check_boolean_feature(USER, Feature.PRIORITY_CACHE)


# ── Expiry revokes entitlement ────────────────────────────────────────────────


async def test_expired_receipt_reverts_to_basic(session: AsyncSession) -> None:
    # Subscription that expired in the past
    past = datetime.now(UTC) - timedelta(days=1)
    expired_receipt = VerifiedReceipt(
        source=BillingSource.APPLE,
        tier=Tier.GOLD,
        provider_subscription_id="txn_expired",
        expires_at=past,
        meta={},
    )
    svc = _svc(session, **{BillingSource.APPLE: StaticReceiptVerifier(result=expired_receipt)})
    sub = await svc.verify_and_upsert(USER, BillingSource.APPLE, "receipt-expired")
    await session.commit()

    # effective_tier checks expires_at — should fall back to BASIC
    assert sub.effective_tier == Tier.BASIC
    assert await svc.get_effective_tier(USER) == Tier.BASIC


async def test_expire_via_service_reverts_to_basic(session: AsyncSession) -> None:
    svc = _svc(session)
    await svc.verify_and_upsert(USER, BillingSource.APPLE, "receipt-gold")
    await session.commit()

    sub = await svc.expire(USER)
    await session.commit()

    assert sub.status == SubscriptionStatus.EXPIRED.value
    assert sub.effective_tier == Tier.BASIC


# ── No subscription → Basic tier ──────────────────────────────────────────────


async def test_no_subscription_is_basic(session: AsyncSession) -> None:
    svc = _svc(session)
    tier = await svc.get_effective_tier("user-no-sub")
    assert tier == Tier.BASIC


# ── Unknown billing source raises ─────────────────────────────────────────────


async def test_unknown_source_raises(session: AsyncSession) -> None:
    svc = SubscriptionService(session, {})  # no verifiers registered
    with pytest.raises(VerificationError, match="No verifier configured"):
        await svc.verify_and_upsert(USER, BillingSource.STRIPE, "sub_xxx")
