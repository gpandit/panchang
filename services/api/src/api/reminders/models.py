"""SQLAlchemy ORM models for the Reminders module."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.reminders.db import Base


class Reminder(Base):
    """A user's recurring reminder rule."""

    __tablename__ = "reminders"

    id: Mapped[uuid.UUID] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[uuid.UUID] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    recurrence: Mapped[dict] = mapped_column(JSON, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    month_scheme: Mapped[str] = mapped_column(String(16), nullable=False, default="amanta")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    occurrences: Mapped[list[DeliveredOccurrence]] = relationship(
        back_populates="reminder", cascade="all, delete-orphan"
    )


class DeliveredOccurrence(Base):
    """Records each delivered fire-time for idempotency.

    `idempotency_key` = "{reminder_id}:{occurrence_date_iso}" is unique — the
    scheduler checks this table before enqueuing to guarantee at-most-once
    delivery per (reminder, occurrence-day) pair.
    """

    __tablename__ = "reminder_delivered_occurrences"

    idempotency_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    reminder_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("reminders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    occurrence_date: Mapped[str] = mapped_column(String(10), nullable=False)  # "YYYY-MM-DD"
    fire_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reminder: Mapped[Reminder] = relationship(back_populates="occurrences")
