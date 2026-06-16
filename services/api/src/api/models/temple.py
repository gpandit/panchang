"""Temple display models — config, location, aarti schedule, events, admin accounts.

A `TempleConfig` is the single source of truth for one temple's Temple Display screen:
its identity, the session location (lat/lon/tz, which drives tithi computation), the
aarti schedule, and a list of events/announcements.

Identity (name / name_dev / tagline) is set by a superuser when the temple is created.
A temple admin edits only the location, aarti schedule, and events (`TempleConfigIn`).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TempleLocation(BaseModel):
    """Session location for the display. lat/lon are used to compute tithi etc."""

    label: str  # human-readable, e.g. "Dubai · United Arab Emirates"
    lat: float
    lon: float
    tz: str  # IANA timezone, e.g. "Asia/Dubai"


class AartiEntry(BaseModel):
    """One row of the aarti schedule. `nat` holds optional per-language names."""

    key: str
    name: str  # transliterated, e.g. "Maṅgala Ārati"
    dev: str  # Devanagari, e.g. "मंगला आरती"
    time: str  # "HH:MM" (24h)
    note: str = ""
    nat: dict[str, str] = Field(default_factory=dict)


class TempleEvent(BaseModel):
    """A temple event/announcement shown on the display."""

    id: str
    title: str
    title_dev: str | None = None
    date: str = ""  # "YYYY-MM-DD"
    time: str | None = None  # "HH:MM"
    description: str | None = None


class TempleConfigIn(BaseModel):
    """Editable subset of a temple, owned by the temple admin."""

    location: TempleLocation
    aarti: list[AartiEntry] = Field(default_factory=list)
    events: list[TempleEvent] = Field(default_factory=list)


class TempleConfig(BaseModel):
    """Full temple record. Identity fields are superuser-managed."""

    id: str
    name: str
    name_dev: str
    tagline: str = ""
    location: TempleLocation
    aarti: list[AartiEntry] = Field(default_factory=list)
    events: list[TempleEvent] = Field(default_factory=list)
    updated_at: datetime
    updated_by: str | None = None


class TempleAdminAccount(BaseModel):
    """A temple-admin login, bound to exactly one temple by a superuser."""

    id: str
    email: str
    password_hash: str
    salt: str
    temple_id: str
    created_at: datetime


# ── Request/response payloads ────────────────────────────────────────────────


class LoginIn(BaseModel):
    email: str
    password: str


class LoginOut(BaseModel):
    token: str
    temple_id: str


class TempleCreateIn(BaseModel):
    """Superuser payload to create a temple."""

    name: str
    name_dev: str
    tagline: str = ""
    location: TempleLocation
    aarti: list[AartiEntry] = Field(default_factory=list)
    events: list[TempleEvent] = Field(default_factory=list)


class AdminAssignIn(BaseModel):
    """Superuser payload to assign an admin login to a temple."""

    email: str
    password: str
