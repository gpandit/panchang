"""FastAPI router for the Reminders module."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.reminders.schemas import ReminderCreate, ReminderRead
from api.reminders.service import ReminderService

router = APIRouter(prefix="/v1/reminders", tags=["reminders"])


# Dependency placeholder — overridden in main.py via dependency_overrides.
async def get_reminder_session() -> AsyncSession:  # pragma: no cover
    raise NotImplementedError


async def get_reminder_service(
    session: AsyncSession = Depends(get_reminder_session),
) -> ReminderService:
    return ReminderService(session)


@router.post("", response_model=ReminderRead, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    payload: ReminderCreate,
    svc: ReminderService = Depends(get_reminder_service),
) -> ReminderRead:
    return await svc.create(payload)


@router.get("/{reminder_id}", response_model=ReminderRead)
async def get_reminder(
    reminder_id: uuid.UUID,
    svc: ReminderService = Depends(get_reminder_service),
) -> ReminderRead:
    reminder = await svc.get(reminder_id)
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return reminder


@router.get("", response_model=list[ReminderRead])
async def list_reminders(
    user_id: uuid.UUID,
    svc: ReminderService = Depends(get_reminder_service),
) -> list[ReminderRead]:
    return await svc.list_for_user(user_id)


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disable_reminder(
    reminder_id: uuid.UUID,
    svc: ReminderService = Depends(get_reminder_service),
) -> None:
    ok = await svc.disable(reminder_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Reminder not found")
