"""Pydantic schemas for the Reminders module.

`RecurrenceSpec` encodes the *rule* — what makes a day eligible.
`ReminderCreate` / `ReminderRead` are the API-facing shapes.
`OccurrenceRead` is a resolved fire-time returned to callers.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, model_validator


class RecurrenceKind(StrEnum):
    GREGORIAN = "gregorian"  # every year on a specific Gregorian month+day
    TITHI = "tithi"  # every occurrence of a Tithi (paksha + index)
    NAKSHATRA = "nakshatra"  # every occurrence of a named Nakshatra
    WEEKDAY = "weekday"  # every occurrence of a weekday (Mon–Sun)


class RecurrenceSpec(BaseModel):
    """What makes a day eligible for this reminder.

    Only fields relevant to the chosen `kind` need to be populated.
    Tithi rules with `paksha=None` match both Shukla and Krishna Paksha
    (e.g. "remind me every Ekadashi").
    """

    kind: RecurrenceKind

    # ── GREGORIAN ──────────────────────────────────────────────────────────
    gregorian_month: int | None = None  # 1–12
    gregorian_day: int | None = None  # 1–31

    # ── TITHI ──────────────────────────────────────────────────────────────
    tithi_index: int | None = None  # 1–15 within the paksha; 11 = Ekadashi
    paksha: str | None = None  # "Shukla Paksha" | "Krishna Paksha" | None → both
    lunar_month: str | None = None  # optional: restrict to a specific lunar month
    observe_in_adhika: bool = False  # whether to observe in Adhika (leap) month

    # ── NAKSHATRA ──────────────────────────────────────────────────────────
    nakshatra_name: str | None = None

    # ── WEEKDAY ────────────────────────────────────────────────────────────
    weekday: int | None = None  # 0 = Monday … 6 = Sunday

    # ── Fire timing ────────────────────────────────────────────────────────
    fire_at_sunrise: bool = True  # True → fire at local sunrise; False → use hour/minute
    fire_hour: int = 6  # local hour when fire_at_sunrise=False
    fire_minute: int = 0  # local minute

    @model_validator(mode="after")
    def _check_fields(self) -> RecurrenceSpec:
        if self.kind is RecurrenceKind.GREGORIAN:
            if self.gregorian_month is None or self.gregorian_day is None:
                raise ValueError("GREGORIAN recurrence requires gregorian_month and gregorian_day")
        if self.kind is RecurrenceKind.TITHI and self.tithi_index is None:
            raise ValueError("TITHI recurrence requires tithi_index")
        if self.kind is RecurrenceKind.NAKSHATRA and self.nakshatra_name is None:
            raise ValueError("NAKSHATRA recurrence requires nakshatra_name")
        if self.kind is RecurrenceKind.WEEKDAY and self.weekday is None:
            raise ValueError("WEEKDAY recurrence requires weekday (0=Mon … 6=Sun)")
        return self


class ReminderCreate(BaseModel):
    title: str
    recurrence: RecurrenceSpec
    timezone: str  # IANA timezone name, e.g. "Asia/Kolkata"
    lat: float
    lon: float
    month_scheme: str = "amanta"
    user_id: UUID


class ReminderRead(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    recurrence: RecurrenceSpec
    timezone: str
    lat: float
    lon: float
    month_scheme: str
    enabled: bool

    model_config = {"from_attributes": True}


class OccurrenceRead(BaseModel):
    """One resolved fire-time for a reminder."""

    reminder_id: UUID
    occurrence_date: str  # ISO date "YYYY-MM-DD" — the Panchang/calendar day
    fire_at: datetime  # UTC datetime when the notification fires
    idempotency_key: str  # "{reminder_id}:{occurrence_date}" — unique per fire
    delivered: bool = False
