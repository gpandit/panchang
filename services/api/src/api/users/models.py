"""ORM models for accounts, auth, preferences and locations.

Birth/family data is deliberately **not** modelled here — see `vault.py`.
No table in this module ever stores a birth date, birth time, birth place,
gotra, or nakshatra.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.users.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AuthProvider(str, Enum):
    PASSWORD = "password"
    GOOGLE = "google"
    APPLE = "apple"
    GUEST = "guest"


class CalendarSystem(str, Enum):
    AMANTA = "amanta"
    PURNIMANTA = "purnimanta"


class TimeForm(str, Enum):
    HOUR_12 = "12h"
    HOUR_24 = "24h"
    HOUR_24_PLUS = "24h_plus"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)

    # Identity — exactly one of (email, phone) is required for non-guest,
    # non-OAuth accounts; OAuth accounts are identified by (provider, provider_subject).
    email: Mapped[str | None] = mapped_column(String(320), unique=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    auth_provider: Mapped[str] = mapped_column(String(16), default=AuthProvider.PASSWORD.value)
    provider_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_guest: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Profile & preferences ─────────────────────────────────────────────
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    preferred_calendar_system: Mapped[str] = mapped_column(
        String(16), default=CalendarSystem.AMANTA.value
    )
    language: Mapped[str] = mapped_column(String(8), default="en")
    time_form: Mapped[str] = mapped_column(String(16), default=TimeForm.HOUR_24.value)
    ayanamsa_override: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notification_settings: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    locations: Mapped[list["Location"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class RefreshToken(Base):
    """Refresh tokens are stored hashed and rotated on every use — a reused
    (already-rotated) token revokes the entire chain (theft detection)."""

    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    user: Mapped[User] = relationship(back_populates="refresh_tokens")

    @property
    def is_active(self) -> bool:
        expires_at = self.expires_at if self.expires_at.tzinfo else self.expires_at.replace(tzinfo=timezone.utc)
        return self.revoked_at is None and expires_at > _now()


class Location(Base):
    """A saved location. Locations drive all Panchang computation, so the
    full (lat, lon, tz, dst rule) tuple is required — never derived client-side."""

    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)

    label: Mapped[str] = mapped_column(String(120))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    tz: Mapped[str] = mapped_column(String(64))  # IANA timezone name
    dst_rule: Mapped[str] = mapped_column(String(32), default="iana")  # 'iana' | 'none' | custom rule id

    is_favourite: Mapped[bool] = mapped_column(Boolean, default=False)
    is_travel_mode: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped[User] = relationship(back_populates="locations")


class AccountAuditLog(Base):
    """Append-only log of account-lifecycle actions (deletion, export, …).

    Distinct from `vault.VaultAccessLog`, which covers sensitive-data access
    specifically; this covers account-level events for compliance review.
    """

    __tablename__ = "account_audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(32))  # 'account_deleted' | 'data_exported'
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
