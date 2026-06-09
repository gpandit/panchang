"""ORM models for subscriptions.

The Subscription row is the canonical record of a user's current tier.
It is always derived from a verified billing receipt — never from client assertions.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.users.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class Tier(StrEnum):
    BASIC = "basic"
    SILVER = "silver"
    GOLD = "gold"


class BillingSource(StrEnum):
    APPLE = "apple"
    GOOGLE = "google"
    STRIPE = "stripe"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    GRACE = "grace"  # billing retry window


class Subscription(Base):
    """One row per user — upserted on every receipt verification.

    For users with no paid subscription, no row exists and the gateway
    treats them as Tier.BASIC.
    """

    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)

    tier: Mapped[str] = mapped_column(String(16), default=Tier.BASIC.value)
    source: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default=SubscriptionStatus.ACTIVE.value)

    # Opaque provider receipt / subscription ID for renewal/cancellation lookups
    provider_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Raw verified receipt stored for audit; never used to re-derive tier at runtime
    raw_receipt: Mapped[str | None] = mapped_column(Text, nullable=True)

    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    # Stores extra provider-specific metadata (product_id, environment, etc.)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    __table_args__ = (Index("ix_subscriptions_user_id_status", "user_id", "status"),)

    @property
    def is_active(self) -> bool:
        if self.status not in (SubscriptionStatus.ACTIVE, SubscriptionStatus.GRACE):
            return False
        if self.expires_at is None:
            return True
        expires_at = (
            self.expires_at
            if self.expires_at.tzinfo
            else self.expires_at.replace(tzinfo=UTC)
        )
        return expires_at > _now()

    @property
    def effective_tier(self) -> Tier:
        if self.is_active:
            return Tier(self.tier)
        return Tier.BASIC
