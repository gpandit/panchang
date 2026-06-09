"""Subscriptions router — exposes tier/receipt verification and entitlement endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from api.subscriptions.entitlements import EntitlementError, Feature, get_limits
from api.subscriptions.models import BillingSource, SubscriptionStatus, Tier
from api.subscriptions.schemas import (
    EntitlementCheckRequest,
    EntitlementResponse,
    SubscriptionResponse,
    VerifyReceiptRequest,
)
from api.subscriptions.service import SubscriptionNotFoundError, SubscriptionService
from api.subscriptions.verifiers import VerificationError

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


# ── Dependency stubs — overridden in main.py ──────────────────────────────────


async def get_subscription_service() -> SubscriptionService:  # pragma: no cover
    raise NotImplementedError("Override get_subscription_service in main.py")


async def get_current_user_id() -> str:  # pragma: no cover
    raise NotImplementedError("Override get_current_user_id in main.py")


# ── Routes ────────────────────────────────────────────────────────────────────


@router.post(
    "/verify",
    response_model=SubscriptionResponse,
    summary="Verify a billing receipt and update subscription",
)
async def verify_receipt(
    body: VerifyReceiptRequest,
    user_id: str = Depends(get_current_user_id),
    svc: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponse:
    """Accept a receipt from Apple, Google, or Stripe and reconcile the subscription."""
    try:
        sub = await svc.verify_and_upsert(user_id, body.source, body.receipt)
    except VerificationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return SubscriptionResponse(
        user_id=sub.user_id,
        tier=Tier(sub.tier),
        source=BillingSource(sub.source),
        status=SubscriptionStatus(sub.status),
        expires_at=sub.expires_at,
        provider_subscription_id=sub.provider_subscription_id,
    )


@router.get(
    "/me",
    response_model=SubscriptionResponse,
    summary="Current user's subscription",
)
async def get_my_subscription(
    user_id: str = Depends(get_current_user_id),
    svc: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponse:
    sub = await svc.get_subscription(user_id)
    if sub is None:
        return SubscriptionResponse(
            user_id=user_id,
            tier=Tier.BASIC,
            source=None,
            status=SubscriptionStatus.ACTIVE,
            expires_at=None,
            provider_subscription_id=None,
        )
    return SubscriptionResponse(
        user_id=sub.user_id,
        tier=sub.effective_tier,
        source=BillingSource(sub.source),
        status=SubscriptionStatus(sub.status),
        expires_at=sub.expires_at,
        provider_subscription_id=sub.provider_subscription_id,
    )


@router.get(
    "/me/entitlements",
    response_model=EntitlementResponse,
    summary="Current user's entitlement limits",
)
async def get_my_entitlements(
    user_id: str = Depends(get_current_user_id),
    svc: SubscriptionService = Depends(get_subscription_service),
) -> EntitlementResponse:
    tier = await svc.get_effective_tier(user_id)
    limits = get_limits(tier)
    return EntitlementResponse(
        tier=tier,
        limits={
            "panchang_lookahead_days": limits.panchang_lookahead_days,
            "saved_locations": limits.saved_locations,
            "active_reminders": limits.active_reminders,
            "festival_notifications_per_month": limits.festival_notifications_per_month,
            "pdf_exports_per_month": limits.pdf_exports_per_month,
            "ai_queries_per_month": limits.ai_queries_per_month,
            "vault_family_members": limits.vault_family_members,
        },
        features={
            "muhurat_planning": limits.muhurat_planning,
            "ad_free": limits.ad_free,
            "priority_cache": limits.priority_cache,
        },
    )


@router.post(
    "/me/check",
    summary="Check a specific entitlement for the current user",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def check_entitlement(
    body: EntitlementCheckRequest,
    user_id: str = Depends(get_current_user_id),
    svc: SubscriptionService = Depends(get_subscription_service),
) -> None:
    """Returns 204 if the user is entitled; 403 if not.

    The API gateway calls this before forwarding to gated domain endpoints.
    """
    try:
        feature = Feature(body.feature)
        limits = get_limits(await svc.get_effective_tier(user_id))
        limit_val = getattr(limits, feature.value)
        if isinstance(limit_val, bool):
            await svc.check_boolean_feature(user_id, feature)
        else:
            await svc.check_quantity_feature(user_id, feature, body.current_count)
    except EntitlementError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post(
    "/me/cancel",
    response_model=SubscriptionResponse,
    summary="Cancel the current user's subscription",
)
async def cancel_subscription(
    user_id: str = Depends(get_current_user_id),
    svc: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponse:
    try:
        sub = await svc.cancel(user_id)
    except SubscriptionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active subscription") from exc
    return SubscriptionResponse(
        user_id=sub.user_id,
        tier=sub.effective_tier,
        source=BillingSource(sub.source),
        status=SubscriptionStatus(sub.status),
        expires_at=sub.expires_at,
        provider_subscription_id=sub.provider_subscription_id,
    )
