"""CRUD /v1/reminders — Tithi/Nakshatra-aware reminders (Silver+)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from api.dependencies import require_tier
from api.models.auth import SubscriptionTier, TokenClaims
from api.models.common import ApiResponse
from api.models.content import ReminderIn, ReminderOut

router = APIRouter(prefix="/reminders", tags=["reminders"])

_silver_dep = require_tier(SubscriptionTier.SILVER)


@router.get("", response_model=ApiResponse[list[ReminderOut]])
async def list_reminders(
    claims: Annotated[TokenClaims, Depends(_silver_dep)],
) -> ApiResponse[list[ReminderOut]]:
    return ApiResponse(data=[])


@router.post("", response_model=ApiResponse[ReminderOut], status_code=status.HTTP_201_CREATED)
async def create_reminder(
    body: ReminderIn,
    claims: Annotated[TokenClaims, Depends(_silver_dep)],
) -> ApiResponse[ReminderOut]:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not yet implemented")


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder_id: Annotated[str, Path()],
    claims: Annotated[TokenClaims, Depends(_silver_dep)],
) -> None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")
