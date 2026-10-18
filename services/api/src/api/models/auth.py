"""JWT token payload, account-role, and subscription-tier models."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class SubscriptionTier(StrEnum):
    """Ordered tiers: basic < silver < gold."""

    BASIC = "basic"
    SILVER = "silver"
    GOLD = "gold"

    def meets(self, required: SubscriptionTier) -> bool:
        order = [SubscriptionTier.BASIC, SubscriptionTier.SILVER, SubscriptionTier.GOLD]
        return order.index(self) >= order.index(required)


class AccountRole(StrEnum):
    """Application roles resolved from the server-side user record."""

    PATRON = "patron"
    PANDIT = "pandit"
    SELLER = "seller"
    ADMIN = "admin"
    OPS = "ops"
    EDITOR = "editor"


class TokenClaims(BaseModel):
    """Decoded JWT payload — the authenticated principal for every request."""

    sub: str  # user UUID
    email: str | None = None
    tier: SubscriptionTier = SubscriptionTier.BASIC
    # Standard JWT claims
    exp: int | None = None
    iat: int | None = None
