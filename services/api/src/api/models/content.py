"""Festival/content, notes, reminders, subscription, and PDF job models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


# ── Festivals ─────────────────────────────────────────────────────────────────

class FestivalOut(BaseModel):
    id: str
    name: str
    date: str  # "YYYY-MM-DD"
    description: str | None
    tags: list[str]


# ── Notes / Bookmarks ─────────────────────────────────────────────────────────

class NoteIn(BaseModel):
    date: str  # "YYYY-MM-DD" the Panchang day this note is anchored to
    body: str
    tags: list[str] = []


class NoteOut(NoteIn):
    id: str
    created_at: datetime
    updated_at: datetime


# ── Reminders ─────────────────────────────────────────────────────────────────

class ReminderIn(BaseModel):
    title: str
    # Either a fixed Gregorian date or a Tithi recurrence expression
    trigger_type: str  # "gregorian" | "tithi" | "nakshatra"
    trigger_value: str  # ISO date or recurrence expression
    advance_minutes: int = 0


class ReminderOut(ReminderIn):
    id: str
    next_fire_at: datetime | None
    is_active: bool


# ── Subscriptions ─────────────────────────────────────────────────────────────

class SubscriptionOut(BaseModel):
    user_id: str
    tier: str  # "basic" | "silver" | "gold"
    valid_until: datetime | None
    features: list[str]


# ── PDF Jobs ──────────────────────────────────────────────────────────────────

class PdfJobIn(BaseModel):
    year: int
    month: int
    lat: float
    lon: float
    tz: str
    ayanamsa: str = "lahiri"
    month_scheme: str = "amanta"


class PdfJobOut(BaseModel):
    job_id: str
    status: str  # "queued" | "processing" | "done" | "failed"
    download_url: str | None = None
    created_at: datetime
