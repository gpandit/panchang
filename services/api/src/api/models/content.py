"""Festival/content, notes, reminders, subscription, and PDF job models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

# ── Festivals ─────────────────────────────────────────────────────────────────


class FestivalOut(BaseModel):
    id: str
    name: str
    date: str  # "YYYY-MM-DD"
    description: str | None
    tags: list[str]
    region: str | None = None
    locale: str | None = None


class FestivalDetailOut(FestivalOut):
    """Full festival record including CMS prose — returned by the detail endpoint."""

    body: str | None = None
    puja: str | None = None
    katha: str | None = None


# ── Notes / Bookmarks ─────────────────────────────────────────────────────────


class NoteIn(BaseModel):
    date: str  # "YYYY-MM-DD" the Panchang day this note is anchored to
    body: str
    tags: list[str] = Field(default_factory=list)

    @field_validator("date")
    @classmethod
    def date_must_be_iso(cls, value: str) -> str:
        from datetime import date

        date.fromisoformat(value)
        return value

    @field_validator("body")
    @classmethod
    def body_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("body must not be blank")
        return value


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
    advance_minutes: int = Field(default=0, ge=0, le=10080)

    @field_validator("trigger_type")
    @classmethod
    def validate_trigger_type(cls, value: str) -> str:
        if value not in {"gregorian", "tithi", "nakshatra"}:
            raise ValueError("trigger_type must be gregorian, tithi, or nakshatra")
        return value


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


class BookmarkIn(BaseModel):
    target_type: str = Field(min_length=1, max_length=64)
    target_id: str = Field(min_length=1, max_length=128)
    category: str = Field(default="calendar", min_length=1, max_length=64)


class BookmarkOut(BookmarkIn):
    id: str
    created_at: datetime


class SubscriptionReceiptIn(BaseModel):
    """Provider-neutral receipt envelope.

    Vendor adapters validate Apple/Google/Stripe payloads before submitting this
    canonical shape. The API deliberately does not pretend to verify vendor
    signatures or contact an external billing service.
    """

    provider: str = Field(min_length=1, max_length=32)
    external_event_id: str = Field(min_length=1, max_length=255)
    provider_ref: str = Field(min_length=1, max_length=255)
    tier: str
    status: str = Field(default="active", min_length=1, max_length=16)
    expires_at: datetime | None = None

    @field_validator("tier")
    @classmethod
    def validate_tier(cls, value: str) -> str:
        if value not in {"basic", "silver", "gold"}:
            raise ValueError("tier must be basic, silver, or gold")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in {"active", "expired", "grace_period", "cancelled"}:
            raise ValueError("unsupported subscription status")
        return value


class SubscriptionReceiptOut(BaseModel):
    provider: str
    external_event_id: str
    provider_ref: str
    status: str
    tier: str
    expires_at: datetime | None
    duplicate: bool = False


# ── PDF Jobs ──────────────────────────────────────────────────────────────────


class PdfJobIn(BaseModel):
    year: int
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
