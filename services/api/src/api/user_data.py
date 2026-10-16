"""Authenticated calendar overlay persistence.

This module is intentionally provider-neutral: JWT subjects are mapped to the
local user row, while billing and notification providers stop at their adapters.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.v3_models import NoteRow, UserRow
from api.models.auth import TokenClaims


async def get_or_create_user(session: AsyncSession, claims: TokenClaims) -> UserRow:
    result = await session.execute(select(UserRow).where(UserRow.auth_subject_ref == claims.sub))
    user = result.scalar_one_or_none()
    if user is None:
        user = UserRow(id=str(uuid.uuid4()), auth_subject_ref=claims.sub, email_ref=claims.email)
        session.add(user)
        await session.flush()
    # PostgreSQL RLS policies use a transaction-local subject.  SQLite has no
    # equivalent setting, so keep the hook a no-op for the offline test path.
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        await session.execute(select(func.set_config("app.user_id", user.id, True)))
    return user


async def count_owned(
    session: AsyncSession,
    model: Any,
    user_id: str,
) -> int:
    column = model.owner_user_id if model is NoteRow else model.user_id
    return int(
        (await session.scalar(select(func.count()).select_from(model).where(column == user_id)))
        or 0
    )


def reminder_next_fire(
    trigger_type: str, trigger_value: str, advance_minutes: int
) -> datetime | None:
    if trigger_type != "gregorian":
        return None
    try:
        value = datetime.fromisoformat(trigger_value.replace("Z", "+00:00"))
    except ValueError:
        value = datetime.combine(date.fromisoformat(trigger_value), datetime.min.time())
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).replace(microsecond=0)


def owned_filter(model: Any, user_id: str) -> Any:
    return (model.owner_user_id if model is NoteRow else model.user_id) == user_id
