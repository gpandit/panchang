"""SubscriptionService — orchestrates receipt verification and entitlement state.

All writes go through this service; the router and gateway call it.
Receipt verifiers are injected so this module is testable without network calls.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.subscriptions.entitlements import (
    Feature,
    TierLimits,
    check_boolean,
    check_quantity,
    get_limits,
)
from api.subscriptions.models import (
    BillingSource,
    Subscription,
    SubscriptionStatus,
    Tier,
)
from api.subscriptions.verifiers import ReceiptVerifier, VerificationError, VerifiedReceipt


class SubscriptionNotFoundError(Exception):
    pass


class SubscriptionService:
    def __init__(
        self,
        session: AsyncSession,
        verifiers: dict[BillingSource, ReceiptVerifier],
    ) -> None:
        self._session = session
        self._verifiers = verifiers

    # ── Receipt verification & upsert ─────────────────────────────────────────

    async def verify_and_upsert(
        self, user_id: str, source: BillingSource, receipt: str
    ) -> Subscription:
        """Verify a billing receipt and reconcile the Subscription record.

        Raises VerificationError if the receipt is invalid.
        Always derives tier from the verified receipt — never from caller input.
        """
        verifier = self._verifiers.get(source)
        if verifier is None:
            raise VerificationError(f"No verifier configured for source={source!r}")

        verified: VerifiedReceipt = await verifier.verify(receipt)
        return await self._upsert_subscription(user_id, verified, raw_receipt=receipt)

    async def _upsert_subscription(
        self,
        user_id: str,
        verified: VerifiedReceipt,
        raw_receipt: str,
    ) -> Subscription:
        result = await self._session.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        sub = result.scalar_one_or_none()

        if sub is None:
            sub = Subscription(user_id=user_id)
            self._session.add(sub)

        sub.tier = verified.tier.value
        sub.source = verified.source.value
        sub.status = SubscriptionStatus.ACTIVE.value
        sub.provider_subscription_id = verified.provider_subscription_id
        sub.expires_at = verified.expires_at
        sub.raw_receipt = raw_receipt
        sub.meta = verified.meta
        sub.updated_at = datetime.now(UTC)

        await self._session.flush()
        return sub

    # ── Cancellation / expiry ─────────────────────────────────────────────────

    async def cancel(self, user_id: str) -> Subscription:
        """Mark the subscription as cancelled; entitlements revert to Basic."""
        sub = await self._get_or_raise(user_id)
        sub.status = SubscriptionStatus.CANCELLED.value
        sub.updated_at = datetime.now(UTC)
        await self._session.flush()
        return sub

    async def expire(self, user_id: str) -> Subscription:
        """Mark the subscription expired (called by renewal-failure webhook)."""
        sub = await self._get_or_raise(user_id)
        sub.status = SubscriptionStatus.EXPIRED.value
        sub.updated_at = datetime.now(UTC)
        await self._session.flush()
        return sub

    # ── Reads ─────────────────────────────────────────────────────────────────

    async def get_subscription(self, user_id: str) -> Subscription | None:
        result = await self._session.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_effective_tier(self, user_id: str) -> Tier:
        sub = await self.get_subscription(user_id)
        if sub is None:
            return Tier.BASIC
        return sub.effective_tier

    # ── Entitlement checks (the gateway calls these) ──────────────────────────

    async def check_boolean_feature(self, user_id: str, feature: Feature) -> None:
        """Raise EntitlementError if the user's tier doesn't have the feature."""
        tier = await self.get_effective_tier(user_id)
        check_boolean(tier, feature)

    async def check_quantity_feature(
        self, user_id: str, feature: Feature, current: int
    ) -> None:
        """Raise EntitlementError if the user has reached the tier limit."""
        tier = await self.get_effective_tier(user_id)
        check_quantity(tier, feature, current)

    async def get_limits(self, user_id: str) -> TierLimits:
        tier = await self.get_effective_tier(user_id)
        return get_limits(tier)

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _get_or_raise(self, user_id: str) -> Subscription:
        sub = await self.get_subscription(user_id)
        if sub is None:
            raise SubscriptionNotFoundError(user_id)
        return sub
