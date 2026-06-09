"""GET /v1/subscription — current user's subscription / entitlement state."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from api.dependencies import require_auth
from api.models.auth import SubscriptionTier, TokenClaims
from api.models.common import ApiResponse
from api.models.content import SubscriptionOut

router = APIRouter(prefix="/subscription", tags=["subscription"])

_FEATURES_BY_TIER: dict[SubscriptionTier, list[str]] = {
    SubscriptionTier.BASIC: ["daily_panchang", "festivals_basic"],
    SubscriptionTier.SILVER: [
        "daily_panchang",
        "festivals_basic",
        "month_calendar",
        "reminders",
        "notes",
    ],
    SubscriptionTier.GOLD: [
        "daily_panchang",
        "festivals_basic",
        "festivals_extended",
        "month_calendar",
        "reminders",
        "notes",
        "pdf_export",
        "ai_assistant",
        "muhurat_planner",
    ],
}


@router.get("", response_model=ApiResponse[SubscriptionOut])
async def get_subscription(
    claims: Annotated[TokenClaims, Depends(require_auth)],
) -> ApiResponse[SubscriptionOut]:
    return ApiResponse(
        data=SubscriptionOut(
            user_id=claims.sub,
            tier=claims.tier.value,
            valid_until=None,
            features=_FEATURES_BY_TIER.get(claims.tier, []),
        )
    )
