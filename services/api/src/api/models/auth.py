"""JWT token payload model and subscription tier enum."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class SubscriptionTier(str, Enum):
    """Ordered tiers: basic < silver < gold."""

    BASIC = "basic"
    SILVER = "silver"
    GOLD = "gold"

    def meets(self, required: "SubscriptionTier") -> bool:
        order = [SubscriptionTier.BASIC, SubscriptionTier.SILVER, SubscriptionTier.GOLD]
        return order.index(self) >= order.index(required)


class TokenClaims(BaseModel):
    """Decoded JWT payload — the authenticated principal for every request."""

    sub: str  # user UUID
    email: str | None = None
    tier: SubscriptionTier = SubscriptionTier.BASIC
    # Standard JWT claims
    exp: int | None = None
    iat: int | None = None
