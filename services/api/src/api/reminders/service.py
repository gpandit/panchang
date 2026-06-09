"""CRUD service for the Reminders module."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.reminders.models import Reminder
from api.reminders.schemas import ReminderCreate, ReminderRead


class ReminderService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, payload: ReminderCreate) -> ReminderRead:
        reminder = Reminder(
            id=str(uuid.uuid4()),
            user_id=str(payload.user_id),
            title=payload.title,
            recurrence=payload.recurrence.model_dump(),
            timezone=payload.timezone,
            lat=payload.lat,
            lon=payload.lon,
            month_scheme=payload.month_scheme,
            enabled=True,
        )
        self._session.add(reminder)
        await self._session.flush()
        return ReminderRead.model_validate(reminder)

    async def get(self, reminder_id: uuid.UUID) -> ReminderRead | None:
        result = await self._session.execute(
            select(Reminder).where(Reminder.id == str(reminder_id))
        )
        reminder = result.scalar_one_or_none()
        return ReminderRead.model_validate(reminder) if reminder else None

    async def list_for_user(self, user_id: uuid.UUID) -> list[ReminderRead]:
        result = await self._session.execute(
            select(Reminder).where(Reminder.user_id == str(user_id))
        )
        return [ReminderRead.model_validate(r) for r in result.scalars().all()]

    async def disable(self, reminder_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            select(Reminder).where(Reminder.id == str(reminder_id))
        )
        reminder = result.scalar_one_or_none()
        if reminder is None:
            return False
        reminder.enabled = False
        await self._session.flush()
        return True
