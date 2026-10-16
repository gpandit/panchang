"""GET /v1/subscription — current user's subscription / entitlement state."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_session
from api.db.v3_models import SubscriptionRow, WebhookReceiptRow
from api.dependencies import require_auth
from api.models.auth import SubscriptionTier, TokenClaims
from api.models.common import ApiResponse
from api.models.content import SubscriptionOut, SubscriptionReceiptIn, SubscriptionReceiptOut
from api.settings import get_settings
from api.user_data import get_or_create_user

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
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[SubscriptionOut]:
    user = await get_or_create_user(session, claims)
    subscription = await session.scalar(
        select(SubscriptionRow)
        .where(
            SubscriptionRow.user_id == user.id,
            SubscriptionRow.status.in_(("active", "grace_period")),
        )
        .order_by(SubscriptionRow.updated_at.desc())
    )
    tier = subscription.tier if subscription is not None else "basic"
    valid_until = subscription.expires_at if subscription is not None else None
    return ApiResponse(
        data=SubscriptionOut(
            user_id=claims.sub,
            tier=tier,
            valid_until=valid_until,
            features=_FEATURES_BY_TIER.get(SubscriptionTier(tier), []),
        )
    )


@router.post("/receipts", response_model=ApiResponse[SubscriptionReceiptOut])
@router.post("/verify-receipt", response_model=ApiResponse[SubscriptionReceiptOut])
async def reconcile_receipt(
    body: SubscriptionReceiptIn,
    claims: Annotated[TokenClaims, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_session)],
    provider_adapter_token: Annotated[str | None, Header(alias="X-Provider-Adapter-Token")] = None,
) -> ApiResponse[SubscriptionReceiptOut]:
    """Reconcile a receipt already normalized by a trusted provider adapter.

    Client applications cannot call this endpoint: the adapter credential is
    deliberately separate from the user's JWT. Apple, Google, and Stripe
    workers validate their vendor payloads before submitting this canonical
    shape. This endpoint stores an idempotent receipt and updates the one active
    subscription for the authenticated user.
    """
    _require_provider_adapter(provider_adapter_token)
    user = await get_or_create_user(session, claims)
    payload_hash = hashlib.sha256(
        json.dumps(body.model_dump(mode="json"), sort_keys=True).encode("utf-8")
    ).hexdigest()
    receipt = await session.scalar(
        select(WebhookReceiptRow).where(
            WebhookReceiptRow.provider == body.provider,
            WebhookReceiptRow.external_event_id == body.external_event_id,
        )
    )
    if receipt is not None:
        if receipt.payload_hash != payload_hash:
            raise HTTPException(status_code=409, detail="Receipt event payload changed")
        owner = await session.scalar(
            select(SubscriptionRow).where(
                SubscriptionRow.source == body.provider,
                SubscriptionRow.provider_ref == body.provider_ref,
                SubscriptionRow.user_id == user.id,
            )
        )
        if owner is None:
            raise HTTPException(
                status_code=409, detail="Receipt event belongs to another account"
            ) from None
        return ApiResponse(data=_receipt_out(body, duplicate=True))

    # The unique provider/event constraint is the replay guard. A savepoint
    # lets a concurrent adapter delivery lose the race without poisoning the
    # request transaction; the winner's row is then read and compared below.
    try:
        async with session.begin_nested():
            session.add(
                WebhookReceiptRow(
                    id=str(uuid.uuid4()),
                    provider=body.provider,
                    external_event_id=body.external_event_id,
                    payload_hash=payload_hash,
                    status="processed",
                    processed_at=datetime.now(UTC),
                )
            )
            await session.flush()
    except IntegrityError:
        receipt = await session.scalar(
            select(WebhookReceiptRow).where(
                WebhookReceiptRow.provider == body.provider,
                WebhookReceiptRow.external_event_id == body.external_event_id,
            )
        )
        if receipt is None:
            raise
        if receipt.payload_hash != payload_hash:
            raise HTTPException(status_code=409, detail="Receipt event payload changed") from None
        owner = await session.scalar(
            select(SubscriptionRow).where(
                SubscriptionRow.source == body.provider,
                SubscriptionRow.provider_ref == body.provider_ref,
                SubscriptionRow.user_id == user.id,
            )
        )
        if owner is None:
            raise HTTPException(
                status_code=409, detail="Receipt event belongs to another account"
            ) from None
        return ApiResponse(data=_receipt_out(body, duplicate=True))

    other_owner = await session.scalar(
        select(SubscriptionRow).where(
            SubscriptionRow.source == body.provider,
            SubscriptionRow.provider_ref == body.provider_ref,
            SubscriptionRow.user_id != user.id,
        )
    )
    if other_owner is not None:
        raise HTTPException(status_code=409, detail="Receipt is already linked to another account")

    current = await session.scalar(
        select(SubscriptionRow).where(
            SubscriptionRow.user_id == user.id,
            SubscriptionRow.source == body.provider,
            SubscriptionRow.provider_ref == body.provider_ref,
        )
    )
    if current is None:
        current = SubscriptionRow(
            id=str(uuid.uuid4()),
            user_id=user.id,
            tier=body.tier,
            source=body.provider,
            provider_ref=body.provider_ref,
            status=body.status,
            expires_at=body.expires_at,
        )
        session.add(current)
    else:
        current.tier = body.tier
        current.status = body.status
        current.expires_at = body.expires_at
    if body.status in {"active", "grace_period"}:
        active = (
            await session.scalars(
                select(SubscriptionRow).where(
                    SubscriptionRow.user_id == user.id,
                    SubscriptionRow.id != current.id,
                    SubscriptionRow.status == "active",
                )
            )
        ).all()
        for row in active:
            row.status = "expired"
    await session.flush()
    return ApiResponse(data=_receipt_out(body))


def _receipt_out(body: SubscriptionReceiptIn, duplicate: bool = False) -> SubscriptionReceiptOut:
    return SubscriptionReceiptOut(
        provider=body.provider,
        external_event_id=body.external_event_id,
        provider_ref=body.provider_ref,
        status=body.status,
        tier=body.tier,
        expires_at=body.expires_at,
        duplicate=duplicate,
    )


def _require_provider_adapter(token: str | None) -> None:
    expected = get_settings().subscription_adapter_token
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Subscription provider adapters are not configured",
        )
    if token is None or not hmac.compare_digest(token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Trusted subscription adapter authentication required",
        )
