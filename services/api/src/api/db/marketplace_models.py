"""ORM models for the "Book a Pandit" marketplace domain (Architecture v1.2 §3).

These mirror the F1 temple models' conventions: string ids, ``JSON_VARIANT`` for
document-style value objects, timezone-aware ``DateTime`` columns, and the shared
:class:`~api.db.base.Base` so Alembic autogenerate and the SQLite test suite both
see every table.

**Portability note.** The no-double-booking guarantee (Architecture north-star #6)
is a Postgres ``ExcludeConstraint`` over a ``tstzrange`` with a ``btree_gist`` GiST
index. That construct is Postgres-only and lives in the Alembic migration
(``0002_marketplace_schema``) rather than here, so ``Base.metadata.create_all`` on the
SQLite test engine does not choke on it. The ORM keeps the two columns it needs
(``start_time``/``end_time``) and a plain composite index; the DB-level overlap
rejection is exercised by a Postgres-gated test.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db.base import JSON_VARIANT, Base

# ── Enumerations (stored as short strings; StrEnum matches the auth.py style) ──


class BookingStatus(StrEnum):
    """The booking lifecycle states (Architecture v1.2 §4 / Addendum A §A5)."""

    REQUESTED = "requested"
    CONFIRMED = "confirmed"
    RESCHEDULE_PENDING = "reschedule_pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED_PATRON = "cancelled_patron"
    CANCELLED_PANDIT = "cancelled_pandit"
    NO_SHOW = "no_show"
    DISPUTED = "disputed"
    REFUNDED = "refunded"
    CLOSED = "closed"


#: Statuses that hold a slot and therefore participate in the no-double-booking
#: exclusion constraint. A slot is "live" from the moment it is requested (the auth
#: is held) through to an active/in-progress ceremony. Terminal/negative states
#: (cancelled, no_show, refunded, closed) release the slot. This tuple is the single
#: source of truth reused by the Alembic migration's partial exclusion predicate.
ACTIVE_BOOKING_STATUSES: tuple[BookingStatus, ...] = (
    BookingStatus.REQUESTED,
    BookingStatus.CONFIRMED,
    BookingStatus.RESCHEDULE_PENDING,
    BookingStatus.IN_PROGRESS,
    BookingStatus.DISPUTED,
)


class ServiceMode(StrEnum):
    IN_PERSON = "in_person"
    LIVE_REMOTE = "live_remote"


class SamagriOption(StrEnum):
    NONE = "none"
    FIXED = "fixed"
    BILLED_AT_COST = "billed_at_cost"


class VerificationStatus(StrEnum):
    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class TravelFeeModel(StrEnum):
    FLAT = "flat"
    PER_MILE = "per_mile"
    BANDED = "banded"


class PaymentStatus(StrEnum):
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    RELEASED = "released"
    REFUNDED = "refunded"
    FAILED = "failed"


class PayoutStatus(StrEnum):
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    PAID = "paid"
    FAILED = "failed"


class ReviewAuthorRole(StrEnum):
    PATRON = "patron"
    PANDIT = "pandit"


class ModerationState(StrEnum):
    PENDING = "pending"
    PUBLISHED = "published"
    HIDDEN = "hidden"
    REMOVED = "removed"


class DisputeState(StrEnum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    CLOSED = "closed"


# A generic money precision. Amounts are minor-unit-safe with Numeric(12, 2); the
# currency lives alongside as an ISO-4217 code column.
_MONEY = Numeric(12, 2)


# ── Provider (Pandit) profile & catalogue ─────────────────────────────────────


class PanditRow(Base):
    __tablename__ = "pandits"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    # References the existing Users domain by id (dual-role — F3). No FK because the
    # user store is not (yet) a table in this DB; kept as an indexed string ref.
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    bio: Mapped[str | None] = mapped_column(String, nullable=True)
    base_location_id: Mapped[str | None] = mapped_column(String, nullable=True)
    languages: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    tradition: Mapped[str | None] = mapped_column(String, nullable=True)
    experience_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    verification_status: Mapped[str] = mapped_column(
        String, nullable=False, default=VerificationStatus.UNVERIFIED.value
    )
    rating_agg: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    rating_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    standing_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    # Vault reference to the Stripe Connect payout account — never a raw account id.
    payout_account_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    services: Mapped[list[PanditServiceRow]] = relationship(
        back_populates="pandit", cascade="all, delete-orphan"
    )
    travel_policy: Mapped[TravelPolicyRow | None] = relationship(
        back_populates="pandit", uselist=False, cascade="all, delete-orphan"
    )
    availability: Mapped[AvailabilityRow | None] = relationship(
        back_populates="pandit", uselist=False, cascade="all, delete-orphan"
    )
    verification_record: Mapped[VerificationRecordRow | None] = relationship(
        back_populates="pandit", uselist=False, cascade="all, delete-orphan"
    )


class ServiceTypeRow(Base):
    """Admin-curated taxonomy; links optional festival/muhurat ids (F5 seeds it)."""

    __tablename__ = "service_types"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    category: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    festival_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    muhurat_event_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    taxonomy_tags: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False, default=list)


class PanditServiceRow(Base):
    __tablename__ = "pandit_services"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    pandit_id: Mapped[str] = mapped_column(
        String, ForeignKey("pandits.id", ondelete="CASCADE"), nullable=False, index=True
    )
    service_type_id: Mapped[str] = mapped_column(
        String, ForeignKey("service_types.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    modes: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False)
    base_price: Mapped[Any] = mapped_column(_MONEY, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    samagri_option: Mapped[str] = mapped_column(
        String, nullable=False, default=SamagriOption.NONE.value
    )
    samagri_price: Mapped[Any | None] = mapped_column(_MONEY, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    pandit: Mapped[PanditRow] = relationship(back_populates="services")


class TravelPolicyRow(Base):
    """One per pandit (§3): willTravel, radius cap ≤100mi, fee model, pickup flag."""

    __tablename__ = "travel_policies"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    pandit_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("pandits.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    will_travel: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Business rule (A3): radius capped at 100 miles — enforced in the service layer;
    # stored as an int for distance/fee math.
    max_radius_miles: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fee_model: Mapped[str] = mapped_column(
        String, nullable=False, default=TravelFeeModel.FLAT.value
    )
    # Fee parameters vary by model (flat amount, per-mile rate, band table) — kept as
    # a JSON document so the schema is stable across fee models.
    fee_config: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict)
    requires_pickup: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    pandit: Mapped[PanditRow] = relationship(back_populates="travel_policy")


class AvailabilityRow(Base):
    """One per pandit: recurrence rules, blackouts, lead time, buffer, accept mode."""

    __tablename__ = "availabilities"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    pandit_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("pandits.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    rules: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict)
    blackout_dates: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    lead_time_min: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    buffer_min: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accept_mode: Mapped[str] = mapped_column(String, nullable=False, default="manual")

    pandit: Mapped[PanditRow] = relationship(back_populates="availability")


class VerificationRecordRow(Base):
    """Statuses only — all raw artefacts live in the Vault (§3, north-star #7)."""

    __tablename__ = "verification_records"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    pandit_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("pandits.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    id_status: Mapped[str] = mapped_column(
        String, nullable=False, default=VerificationStatus.UNVERIFIED.value
    )
    bg_check_status: Mapped[str] = mapped_column(
        String, nullable=False, default=VerificationStatus.UNVERIFIED.value
    )
    address_status: Mapped[str] = mapped_column(
        String, nullable=False, default=VerificationStatus.UNVERIFIED.value
    )
    # Vault references to the verification artefacts — never the raw docs/reports.
    vault_refs: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict)
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    pandit: Mapped[PanditRow] = relationship(back_populates="verification_record")


# ── Bookings & lifecycle ──────────────────────────────────────────────────────


class BookingRow(Base):
    __tablename__ = "bookings"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    patron_user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    pandit_id: Mapped[str] = mapped_column(
        String, ForeignKey("pandits.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    pandit_service_id: Mapped[str] = mapped_column(
        String, ForeignKey("pandit_services.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    mode: Mapped[str] = mapped_column(String, nullable=False)
    # start_time/end_time back the tstzrange used by the no-double-booking exclusion
    # constraint (added in the migration, Postgres-only). end_time is derived from the
    # service duration + travel buffer at booking time.
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tz: Mapped[str] = mapped_column(String, nullable=False)
    # Vault reference to the exact ceremony address (revealed to pandit only after
    # confirmed+paid — §6 address privacy). Never the raw address.
    address_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    samagri_chosen: Mapped[str] = mapped_column(
        String, nullable=False, default=SamagriOption.NONE.value
    )
    status: Mapped[str] = mapped_column(
        String, nullable=False, default=BookingStatus.REQUESTED.value, index=True
    )
    # Server-authoritative itemised quote (base + travel + samagri + fee + tax).
    price_breakdown: Mapped[dict[str, Any]] = mapped_column(
        JSON_VARIANT, nullable=False, default=dict
    )
    # Immutable snapshot of the cancellation/refund + fee terms at booking time
    # (§2 policy immutability). JSONB on Postgres.
    policy_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON_VARIANT, nullable=False, default=dict
    )
    muhurat_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    sankalp: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    events: Mapped[list[BookingEventRow]] = relationship(
        back_populates="booking", cascade="all, delete-orphan"
    )
    payment: Mapped[PaymentRow | None] = relationship(
        back_populates="booking", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        # A plain composite index that helps availability lookups on SQLite and
        # Postgres alike. The overlap *rejection* is the ExcludeConstraint added in
        # the migration (Postgres-only).
        Index("ix_bookings_pandit_start", "pandit_id", "start_time"),
    )


class BookingEventRow(Base):
    """Lifecycle audit — one row per transition, written in the same txn (§4/§A5)."""

    __tablename__ = "booking_events"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    booking_id: Mapped[str] = mapped_column(
        String, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_state: Mapped[str | None] = mapped_column(String, nullable=True)
    to_state: Mapped[str] = mapped_column(String, nullable=False)
    actor: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    booking: Mapped[BookingRow] = relationship(back_populates="events")


# ── Money: payments, payouts, refunds (append-only, auditable — §2) ───────────


class PaymentRow(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    booking_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("bookings.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True,
    )
    # Stripe object references (PaymentIntent, charge, etc.) — no raw card data.
    stripe_refs: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict)
    amount: Mapped[Any] = mapped_column(_MONEY, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    commission: Mapped[Any] = mapped_column(_MONEY, nullable=False, default=0)
    taxes: Mapped[Any] = mapped_column(_MONEY, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default=PaymentStatus.AUTHORIZED.value, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    booking: Mapped[BookingRow] = relationship(back_populates="payment")


class PayoutRow(Base):
    __tablename__ = "payouts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    pandit_id: Mapped[str] = mapped_column(
        String, ForeignKey("pandits.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    amount: Mapped[Any] = mapped_column(_MONEY, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default=PayoutStatus.PENDING.value, index=True
    )
    # Vault/object-store reference to the downloadable statement.
    statement_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    stripe_refs: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RefundRow(Base):
    __tablename__ = "refunds"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    booking_id: Mapped[str] = mapped_column(
        String, ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    amount: Mapped[Any] = mapped_column(_MONEY, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    # Which cancellation-policy tier drove the amount (from the booking's snapshot).
    policy_tier: Mapped[str | None] = mapped_column(String, nullable=True)
    stripe_refs: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ── Reviews ───────────────────────────────────────────────────────────────────


class ReviewRow(Base):
    """Two-way, verified-booking, double-blind reveal (§3 / D3)."""

    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    booking_id: Mapped[str] = mapped_column(
        String, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_role: Mapped[str] = mapped_column(String, nullable=False)
    stars: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[str | None] = mapped_column(String, nullable=True)
    moderation_state: Mapped[str] = mapped_column(
        String, nullable=False, default=ModerationState.PENDING.value, index=True
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        # At most one review per (booking, author role) — a patron and a pandit may
        # each review a booking exactly once (up to two per booking, §3.1).
        UniqueConstraint("booking_id", "author_role", name="uq_review_booking_author"),
    )


# ── Messaging ─────────────────────────────────────────────────────────────────


class ConversationRow(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    # Nullable — pre-booking Q&A conversations have no booking yet (§3, D1).
    booking_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True, index=True
    )
    participants: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    messages: Mapped[list[MessageRow]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class MessageRow(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender_user_id: Mapped[str] = mapped_column(String, nullable=False)
    # Body is stored PII-masked (D1); the object-store ref carries any attachment.
    body: Mapped[str | None] = mapped_column(String, nullable=True)
    attachment_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    # Moderation/leak-detection flags (phone/email/off-platform circumvention).
    flags: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    conversation: Mapped[ConversationRow] = relationship(back_populates="messages")


# ── Live video (Phase 2 fast-follow) ──────────────────────────────────────────


class VideoSessionRow(Base):
    __tablename__ = "video_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    booking_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    provider: Mapped[str | None] = mapped_column(String, nullable=True)
    join_window_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    join_window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # join/leave events feeding completion/no-show resolution.
    join_log: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON_VARIANT, nullable=False, default=list
    )
    # Object-store ref for an optional, both-party-consented recording.
    recording_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ── Disputes ──────────────────────────────────────────────────────────────────


class DisputeRow(Base):
    """Opening a dispute freezes the payout (§4 / D4)."""

    __tablename__ = "disputes"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    booking_id: Mapped[str] = mapped_column(
        String, ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    raised_by: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    # Vault/object-store refs to evidence (messages, session logs, photos).
    evidence_refs: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    state: Mapped[str] = mapped_column(
        String, nullable=False, default=DisputeState.OPEN.value, index=True
    )
    resolution: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
