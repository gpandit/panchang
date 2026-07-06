"""JWT token payload model, subscription tier enum, and marketplace role enum."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SubscriptionTier(StrEnum):
    """Ordered tiers: basic < silver < gold."""

    BASIC = "basic"
    SILVER = "silver"
    GOLD = "gold"

    def meets(self, required: SubscriptionTier) -> bool:
        order = [SubscriptionTier.BASIC, SubscriptionTier.SILVER, SubscriptionTier.GOLD]
        return order.index(self) >= order.index(required)


class Role(StrEnum):
    """Marketplace identity roles carried on the JWT (F3 — dual-role identity).

    A single login can hold *any combination* of these — the set is unordered
    (unlike :class:`SubscriptionTier` / :class:`~api.models.admin.AdminRole`,
    which are graduated). ``PATRON`` books ceremonies; ``PANDIT`` provides them;
    ``ADMIN`` mirrors the marketplace-operator capability. Fine-grained admin
    RBAC still lives in :class:`~api.models.admin.AdminRole` via the separate
    ``admin_role`` claim — ``Role.ADMIN`` here just marks operator identity and
    does not clobber that ladder.
    """

    PATRON = "patron"
    PANDIT = "pandit"
    ADMIN = "admin"


class TokenClaims(BaseModel):
    """Decoded JWT payload — the authenticated principal for every request."""

    sub: str  # user UUID
    email: str | None = None
    tier: SubscriptionTier = SubscriptionTier.BASIC
    # Marketplace roles this login holds (F3). A set so membership tests are O(1)
    # and order-independent; defaults to empty for legacy (pre-marketplace) tokens.
    roles: set[Role] = Field(default_factory=set)
    # Standard JWT claims
    exp: int | None = None
    iat: int | None = None

    def has_role(self, role: Role) -> bool:
        """True if this principal holds ``role``."""
        return role in self.roles
