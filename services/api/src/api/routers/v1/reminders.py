"""CRUD /v1/reminders — Tithi/Nakshatra-aware reminders (Silver+)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_session
from api.db.v3_models import ReminderRow
from api.dependencies import require_tier
from api.models.auth import SubscriptionTier, TokenClaims
from api.models.common import ApiResponse
from api.models.content import ReminderIn, ReminderOut
from api.user_data import count_owned, get_or_create_user, owned_filter, reminder_next_fire

router = APIRouter(prefix="/reminders", tags=["reminders"])

_silver_dep = require_tier(SubscriptionTier.SILVER)


@router.get("", response_model=ApiResponse[list[ReminderOut]])
async def list_reminders(
    claims: Annotated[TokenClaims, Depends(_silver_dep)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[list[ReminderOut]]:
    user = await get_or_create_user(session, claims)
    rows = (
        await session.scalars(
            select(ReminderRow)
            .where(owned_filter(ReminderRow, user.id))
            .order_by(ReminderRow.next_fire_at)
        )
    ).all()
    return ApiResponse(data=[_out(row) for row in rows])


@router.post("", response_model=ApiResponse[ReminderOut], status_code=status.HTTP_201_CREATED)
async def create_reminder(
    body: ReminderIn,
    claims: Annotated[TokenClaims, Depends(_silver_dep)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[ReminderOut]:
    user = await get_or_create_user(session, claims)
    if claims.tier.value == "basic" and await count_owned(session, ReminderRow, user.id) >= 5:
        raise HTTPException(
            status_code=403, detail={"code": "quota_exceeded", "resource": "reminders"}
        )
    next_fire = _validated_next_fire(body)
    row = ReminderRow(
        id=str(uuid.uuid4()),
        user_id=user.id,
        recurrence_spec=body.model_dump(),
        next_fire_at=next_fire,
        fire_key=str(uuid.uuid4()),
        active=True,
    )
    session.add(row)
    await session.flush()
    return ApiResponse(data=_out(row))


@router.get("/{reminder_id}", response_model=ApiResponse[ReminderOut])
async def get_reminder(
    reminder_id: Annotated[str, Path()],
    claims: Annotated[TokenClaims, Depends(_silver_dep)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[ReminderOut]:
    user = await get_or_create_user(session, claims)
    row = await session.scalar(
        select(ReminderRow).where(ReminderRow.id == reminder_id, owned_filter(ReminderRow, user.id))
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return ApiResponse(data=_out(row))


@router.put("/{reminder_id}", response_model=ApiResponse[ReminderOut])
async def update_reminder(
    reminder_id: Annotated[str, Path()],
    body: ReminderIn,
    claims: Annotated[TokenClaims, Depends(_silver_dep)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[ReminderOut]:
    user = await get_or_create_user(session, claims)
    row = await session.scalar(
        select(ReminderRow).where(ReminderRow.id == reminder_id, owned_filter(ReminderRow, user.id))
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    next_fire = _validated_next_fire(body)
    row.recurrence_spec = body.model_dump()
    row.next_fire_at = next_fire
    row.fire_key = str(uuid.uuid4())
    await session.flush()
    return ApiResponse(data=_out(row))


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder_id: Annotated[str, Path()],
    claims: Annotated[TokenClaims, Depends(_silver_dep)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    user = await get_or_create_user(session, claims)
    row = await session.scalar(
        select(ReminderRow).where(ReminderRow.id == reminder_id, owned_filter(ReminderRow, user.id))
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")
    row.active = False


def _out(row: ReminderRow) -> ReminderOut:
    spec = row.recurrence_spec or {}
    return ReminderOut(
        id=row.id,
        title=str(spec.get("title", "")),
        trigger_type=str(spec.get("trigger_type", "gregorian")),
        trigger_value=str(spec.get("trigger_value", "")),
        advance_minutes=int(spec.get("advance_minutes", 0)),
        next_fire_at=row.next_fire_at,
        is_active=row.active,
    )


def _validated_next_fire(body: ReminderIn) -> datetime | None:
    try:
        next_fire = reminder_next_fire(body.trigger_type, body.trigger_value, body.advance_minutes)
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail="trigger_value is not a valid ISO date/time"
        ) from exc
    if next_fire is not None:
        next_fire -= timedelta(minutes=body.advance_minutes)
    return next_fire
