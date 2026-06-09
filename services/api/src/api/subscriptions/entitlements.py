"""Entitlement definitions and check functions.

This is the single source of truth for "can this user do X".
The API gateway (Step 3.1) calls `EntitlementService.check()` on every
gated endpoint — it never reads the tier directly from the request.

Limit encoding: -1 means unlimited.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from api.subscriptions.models import Tier


class Feature(StrEnum):
    PANCHANG_LOOKAHEAD_DAYS = "panchang_lookahead_days"
    SAVED_LOCATIONS = "saved_locations"
    ACTIVE_REMINDERS = "active_reminders"
    FESTIVAL_NOTIFICATIONS_PER_MONTH = "festival_notifications_per_month"
    PDF_EXPORTS_PER_MONTH = "pdf_exports_per_month"
    AI_QUERIES_PER_MONTH = "ai_queries_per_month"
    VAULT_FAMILY_MEMBERS = "vault_family_members"
    MUHURAT_PLANNING = "muhurat_planning"
    AD_FREE = "ad_free"
    PRIORITY_CACHE = "priority_cache"


@dataclass(frozen=True)
class TierLimits:
    panchang_lookahead_days: int
    saved_locations: int  # -1 = unlimited
    active_reminders: int
    festival_notifications_per_month: int
    pdf_exports_per_month: int
    ai_queries_per_month: int
    vault_family_members: int
    muhurat_planning: bool
    ad_free: bool
    priority_cache: bool


_UNLIMITED = -1

TIER_LIMITS: dict[Tier, TierLimits] = {
    Tier.BASIC: TierLimits(
        panchang_lookahead_days=7,
        saved_locations=1,
        active_reminders=5,
        festival_notifications_per_month=5,
        pdf_exports_per_month=0,
        ai_queries_per_month=0,
        vault_family_members=1,
        muhurat_planning=False,
        ad_free=False,
        priority_cache=False,
    ),
    Tier.SILVER: TierLimits(
        panchang_lookahead_days=90,
        saved_locations=3,
        active_reminders=25,
        festival_notifications_per_month=20,
        pdf_exports_per_month=1,
        ai_queries_per_month=5,
        vault_family_members=5,
        muhurat_planning=True,
        ad_free=True,
        priority_cache=False,
    ),
    Tier.GOLD: TierLimits(
        panchang_lookahead_days=365,
        saved_locations=_UNLIMITED,
        active_reminders=_UNLIMITED,
        festival_notifications_per_month=_UNLIMITED,
        pdf_exports_per_month=_UNLIMITED,
        ai_queries_per_month=_UNLIMITED,
        vault_family_members=_UNLIMITED,
        muhurat_planning=True,
        ad_free=True,
        priority_cache=True,
    ),
}


class EntitlementError(Exception):
    """Raised when a user does not have entitlement for a feature/quantity."""

    def __init__(self, feature: Feature, tier: Tier, limit: int | bool) -> None:
        self.feature = feature
        self.tier = tier
        self.limit = limit
        super().__init__(
            f"Tier '{tier}' does not allow '{feature}' (limit={limit})"
        )


def get_limits(tier: Tier) -> TierLimits:
    return TIER_LIMITS[tier]


def check_boolean(tier: Tier, feature: Feature) -> None:
    """Raise EntitlementError if the feature flag is False for this tier."""
    limits = get_limits(tier)
    value: bool = getattr(limits, feature.value)
    if not value:
        raise EntitlementError(feature, tier, False)


def check_quantity(tier: Tier, feature: Feature, current: int) -> None:
    """Raise EntitlementError if adding one more would exceed the tier limit.

    `current` is the user's present count (before the action being gated).
    Unlimited features (limit == -1) always pass.
    """
    limits = get_limits(tier)
    limit: int = getattr(limits, feature.value)
    if limit == _UNLIMITED:
        return
    if current >= limit:
        raise EntitlementError(feature, tier, limit)


def is_allowed_boolean(tier: Tier, feature: Feature) -> bool:
    try:
        check_boolean(tier, feature)
        return True
    except EntitlementError:
        return False


def is_allowed_quantity(tier: Tier, feature: Feature, current: int) -> bool:
    try:
        check_quantity(tier, feature, current)
        return True
    except EntitlementError:
        return False
