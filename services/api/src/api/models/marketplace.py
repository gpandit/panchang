"""Pydantic schemas for the "Book a Pandit" marketplace domain (Architecture v1.2 §3).

These follow the existing ``api/models`` style (``*In`` for request bodies, ``*Out``
for responses, ``BaseModel`` subclasses, ``StrEnum`` for closed vocabularies). They are
the API contract; the ORM rows in :mod:`api.db.marketplace_models` are the persistence
shape. Sensitive fields (exact addresses, ID/background-check artefacts) are represented
only as vault *references* here — the raw values are never serialized to clients (§3).

The enums are re-exported from the ORM module so there is a single source of truth for
the vocabularies (booking states, modes, statuses) shared by persistence and the API.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from api.db.marketplace_models import (
    BookingStatus,
    DisputeState,
    ModerationState,
    PaymentStatus,
    PayoutStatus,
    ReviewAuthorRole,
    SamagriOption,
    ServiceMode,
    TravelFeeModel,
    VerificationStatus,
)

__all__ = [  # noqa: RUF022 — grouped by domain (enums, catalogue, bookings, …) not alphabetical
    "BookingStatus",
    "DisputeState",
    "ModerationState",
    "PaymentStatus",
    "PayoutStatus",
    "ReviewAuthorRole",
    "SamagriOption",
    "ServiceMode",
    "TravelFeeModel",
    "VerificationStatus",
    # Pandit / catalogue
    "PanditOut",
    "PanditServiceIn",
    "PanditServiceOut",
    "ServiceTypeOut",
    "TravelPolicyIn",
    "TravelPolicyOut",
    "AvailabilityIn",
    "AvailabilityOut",
    "VerificationRecordOut",
    # Bookings
    "BookingCreateIn",
    "BookingOut",
    "BookingEventOut",
    "PriceBreakdown",
    # Money
    "PaymentOut",
    "PayoutOut",
    "RefundOut",
    # Reviews / messaging / video / disputes
    "ReviewIn",
    "ReviewOut",
    "ConversationOut",
    "MessageIn",
    "MessageOut",
    "VideoSessionOut",
    "DisputeIn",
    "DisputeOut",
]


# ── Pandit profile & catalogue ────────────────────────────────────────────────


class ServiceTypeOut(BaseModel):
    id: str
    category: str
    name: str
    festival_ref: str | None = None
    muhurat_event_ref: str | None = None
    taxonomy_tags: list[str] = []


class TravelPolicyIn(BaseModel):
    will_travel: bool = False
    max_radius_miles: int = Field(0, ge=0, le=100)  # A3 hard cap: ≤100 miles
    fee_model: TravelFeeModel = TravelFeeModel.FLAT
    fee_config: dict[str, Any] = {}
    requires_pickup: bool = False


class TravelPolicyOut(TravelPolicyIn):
    id: str
    pandit_id: str


class PanditServiceIn(BaseModel):
    service_type_id: str
    modes: list[ServiceMode]
    duration_min: int = Field(..., gt=0)
    base_price: Decimal = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=3)
    samagri_option: SamagriOption = SamagriOption.NONE
    samagri_price: Decimal | None = None


class PanditServiceOut(PanditServiceIn):
    id: str
    pandit_id: str
    is_published: bool
    created_at: datetime
    updated_at: datetime


class PanditOut(BaseModel):
    """Public-safe pandit projection — no vault refs, no exact location."""

    id: str
    display_name: str
    bio: str | None = None
    languages: list[str] = []
    tradition: str | None = None
    experience_years: int | None = None
    verification_status: VerificationStatus
    rating_agg: float | None = None
    rating_count: int = 0
    standing_score: float | None = None


class AvailabilityIn(BaseModel):
    rules: dict[str, Any] = {}
    blackout_dates: list[str] = []
    lead_time_min: int = Field(0, ge=0)
    buffer_min: int = Field(0, ge=0)
    accept_mode: str = "manual"  # "manual" | "auto"


class AvailabilityOut(AvailabilityIn):
    id: str
    pandit_id: str


class VerificationRecordOut(BaseModel):
    """Statuses only — vault references are never exposed to clients (§3)."""

    id: str
    pandit_id: str
    id_status: VerificationStatus
    bg_check_status: VerificationStatus
    address_status: VerificationStatus
    last_verified_at: datetime | None = None


# ── Bookings ──────────────────────────────────────────────────────────────────


class PriceBreakdown(BaseModel):
    """Server-authoritative itemised quote (§A4.5). The client never sets these."""

    base: Decimal
    travel: Decimal = Decimal("0")
    samagri: Decimal = Decimal("0")
    platform_fee: Decimal = Decimal("0")
    tax: Decimal = Decimal("0")
    total: Decimal
    currency: str = Field(..., min_length=3, max_length=3)


class BookingCreateIn(BaseModel):
    """Booking request. Notably absent: any price field — money is server-side (§0)."""

    pandit_service_id: str
    mode: ServiceMode
    start_time: datetime
    tz: str
    # Address is captured for in-person bookings and stored as a vault ref server-side.
    address_ref: str | None = None
    samagri_chosen: SamagriOption = SamagriOption.NONE
    muhurat_ref: str | None = None
    sankalp: str | None = None
    notes: str | None = None


class BookingOut(BaseModel):
    id: str
    patron_user_id: str
    pandit_id: str
    pandit_service_id: str
    mode: ServiceMode
    start_time: datetime
    end_time: datetime
    tz: str
    samagri_chosen: SamagriOption
    status: BookingStatus
    price_breakdown: PriceBreakdown | None = None
    muhurat_ref: str | None = None
    created_at: datetime
    updated_at: datetime
    # NB: address_ref and policy_snapshot are intentionally omitted from the default
    # client projection (address privacy §6; snapshot is internal accounting data).


class BookingEventOut(BaseModel):
    id: str
    booking_id: str
    from_state: BookingStatus | None = None
    to_state: BookingStatus
    actor: str
    reason: str | None = None
    created_at: datetime


# ── Money ─────────────────────────────────────────────────────────────────────


class PaymentOut(BaseModel):
    id: str
    booking_id: str
    amount: Decimal
    currency: str
    commission: Decimal
    taxes: Decimal
    status: PaymentStatus
    created_at: datetime
    updated_at: datetime


class PayoutOut(BaseModel):
    id: str
    pandit_id: str
    amount: Decimal
    currency: str
    period_start: datetime | None = None
    period_end: datetime | None = None
    status: PayoutStatus
    statement_ref: str | None = None
    created_at: datetime


class RefundOut(BaseModel):
    id: str
    booking_id: str
    amount: Decimal
    currency: str
    reason: str | None = None
    policy_tier: str | None = None
    created_at: datetime


# ── Reviews / messaging / video / disputes ────────────────────────────────────


class ReviewIn(BaseModel):
    stars: int = Field(..., ge=1, le=5)
    body: str | None = None


class ReviewOut(BaseModel):
    id: str
    booking_id: str
    author_role: ReviewAuthorRole
    stars: int
    body: str | None = None
    moderation_state: ModerationState
    published_at: datetime | None = None
    created_at: datetime


class ConversationOut(BaseModel):
    id: str
    booking_id: str | None = None
    participants: list[str] = []
    created_at: datetime


class MessageIn(BaseModel):
    body: str | None = None
    attachment_ref: str | None = None


class MessageOut(BaseModel):
    id: str
    conversation_id: str
    sender_user_id: str
    body: str | None = None
    attachment_ref: str | None = None
    flags: dict[str, Any] = {}
    created_at: datetime


class VideoSessionOut(BaseModel):
    id: str
    booking_id: str
    provider: str | None = None
    join_window_start: datetime | None = None
    join_window_end: datetime | None = None
    recording_ref: str | None = None
    created_at: datetime


class DisputeIn(BaseModel):
    reason: str | None = None
    evidence_refs: list[str] = []


class DisputeOut(BaseModel):
    id: str
    booking_id: str
    raised_by: str
    reason: str | None = None
    state: DisputeState
    resolution: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None
