"""SQLAlchemy schema for the v3.0 persistence foundation.

This module deliberately contains *references* to Vault/provider data, never the
payloads themselves.  The types used here are portable to SQLite so migration and
model tests can run without a service dependency; PostgreSQL gets JSONB and the
PostGIS/range types used by production.  Domain behavior (Vault access, outbox
publishing, booking state transitions, and provider calls) belongs to later stages.
"""

from __future__ import annotations

from datetime import date as DateValue, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    BigInteger,
    CheckConstraint,
    DDL,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    event,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator, UserDefinedType

from api.db.base import JSON_VARIANT, Base


class GeographyPoint(UserDefinedType):
    """PostGIS point type; SQLite accepts the name as an ordinary fallback type."""

    cache_ok = True

    def get_col_spec(self, **_: Any) -> str:
        return "GEOGRAPHY(POINT,4326)"


class GeoPoint(TypeDecorator[str]):
    """Use PostGIS geography in production and text in SQLite tests."""

    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(GeographyPoint())
        return dialect.type_descriptor(String(96))


class TimestampRange(TypeDecorator[str]):
    """PostgreSQL ``tstzrange`` with a portable SQLite text fallback."""

    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.TSTZRANGE())
        return dialect.type_descriptor(String(160))


UUID = postgresql.UUID(as_uuid=False).with_variant(String(36), "sqlite")
MONEY = BigInteger()
UTC = DateTime(timezone=True)


def _id() -> Mapped[str]:
    return mapped_column(UUID, primary_key=True)


def _created() -> Mapped[datetime]:
    return mapped_column(UTC, nullable=False, server_default=text("CURRENT_TIMESTAMP"))


def _updated() -> Mapped[datetime]:
    return mapped_column(
        UTC,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
    )


class UserRow(Base):
    __tablename__ = "users"
    id = _id()
    auth_subject_ref: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    email_ref: Mapped[str | None] = mapped_column(String(255), unique=True)
    phone_ref: Mapped[str | None] = mapped_column(String(255), unique=True)
    display_name: Mapped[str | None] = mapped_column(String(200))
    locale: Mapped[str] = mapped_column(String(16), nullable=False, server_default="en")
    tier: Mapped[str] = mapped_column(String(16), nullable=False, server_default="basic")
    roles: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    created_at = _created()
    updated_at = _updated()
    __table_args__ = (CheckConstraint("tier IN ('basic','silver','gold')", name="ck_users_tier"),)


class UserPreferenceRow(Base):
    __tablename__ = "user_preferences"
    user_id: Mapped[str] = mapped_column(UUID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    scheme: Mapped[str] = mapped_column(String(32), nullable=False, server_default="amanta")
    ayanamsa: Mapped[str] = mapped_column(String(32), nullable=False, server_default="lahiri")
    calendar_style: Mapped[str] = mapped_column(String(32), nullable=False, server_default="gregorian")
    notification_settings: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict)
    created_at = _created()
    updated_at = _updated()


class LocationRow(Base):
    __tablename__ = "locations"
    id = _id()
    user_id: Mapped[str] = mapped_column(UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    lat: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    lon: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    point: Mapped[str | None] = mapped_column(GeoPoint())
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    created_at = _created()
    updated_at = _updated()
    __table_args__ = (
        CheckConstraint("lat >= -90 AND lat <= 90", name="ck_locations_latitude"),
        CheckConstraint("lon >= -180 AND lon <= 180", name="ck_locations_longitude"),
        Index("ix_locations_user", "user_id"),
        Index("uq_locations_primary_user", "user_id", unique=True, sqlite_where=text("is_primary = 1"), postgresql_where=text("is_primary = true")),
    )


class FamilyGroupRow(Base):
    __tablename__ = "family_groups"
    id = _id()
    owner_user_id: Mapped[str] = mapped_column(UUID, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_at = _created()
    updated_at = _updated()


class FamilyMembershipRow(Base):
    __tablename__ = "family_memberships"
    id = _id()
    group_id: Mapped[str] = mapped_column(UUID, ForeignKey("family_groups.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, server_default="member")
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="invited")
    invited_at: Mapped[datetime | None] = mapped_column(UTC)
    accepted_at: Mapped[datetime | None] = mapped_column(UTC)
    created_at = _created()
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_family_membership"),)


class VaultRefRow(Base):
    __tablename__ = "vault_refs"
    id = _id()
    subject_type: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_id: Mapped[str] = mapped_column(UUID, nullable=False)
    region: Mapped[str] = mapped_column(String(32), nullable=False)
    purpose: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at = _created()
    __table_args__ = (UniqueConstraint("subject_type", "subject_id", "purpose", name="uq_vault_subject_purpose"),)


class VaultAccessLogRow(Base):
    __tablename__ = "vault_access_log"
    id = _id()
    vault_ref_id: Mapped[str] = mapped_column(UUID, ForeignKey("vault_refs.id"), nullable=False)
    actor_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    purpose: Mapped[str] = mapped_column(String(128), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(UTC, nullable=False)
    __table_args__ = (Index("ix_vault_access_log_ref_time", "vault_ref_id", "occurred_at"),)


class IdempotencyKeyRow(Base):
    """A replay record containing references and hashes, never a response body.

    ``scope`` separates keys used by different commands/tenants.  The unique
    scope/key pair is the database-level replay guard; response and resource
    references point at durable data owned by the calling domain.
    """

    __tablename__ = "idempotency_keys"
    id = _id()
    scope: Mapped[str] = mapped_column(String(255), nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, server_default="pending")
    response_ref: Mapped[str | None] = mapped_column(String(512))
    resource_ref: Mapped[str | None] = mapped_column(String(512))
    response_status: Mapped[int | None] = mapped_column(Integer)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(UTC)
    completed_at: Mapped[datetime | None] = mapped_column(UTC)
    created_at = _created()
    updated_at = _updated()
    __table_args__ = (
        UniqueConstraint("scope", "key", name="uq_idempotency_scope_key"),
        CheckConstraint("state IN ('pending','completed','failed')", name="ck_idempotency_state"),
        CheckConstraint("attempts >= 0", name="ck_idempotency_attempts"),
        Index("ix_idempotency_expiry", "state", "expires_at"),
    )


class OutboxEventRow(Base):
    """Durable event envelope for publication after its source transaction commits.

    The envelope intentionally has no JSON payload column.  ``payload_ref`` is
    an opaque object-store/database reference and is the only payload handle a
    worker receives from this table.
    """

    __tablename__ = "outbox_events"
    id = _id()
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    payload_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    # Producers can supply a stable command/event key.  It is nullable so two
    # legitimate events of the same type may coexist when no dedupe contract
    # exists; the event id remains unique in all cases.
    dedupe_key: Mapped[str | None] = mapped_column(String(255), unique=True)
    idempotency_key_id: Mapped[str | None] = mapped_column(
        UUID, ForeignKey("idempotency_keys.id", ondelete="SET NULL")
    )
    state: Mapped[str] = mapped_column(String(16), nullable=False, server_default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    available_at: Mapped[datetime | None] = mapped_column(UTC)
    claimed_at: Mapped[datetime | None] = mapped_column(UTC)
    claimed_by: Mapped[str | None] = mapped_column(String(255))
    last_error: Mapped[str | None] = mapped_column(Text)
    processed_at: Mapped[datetime | None] = mapped_column(UTC)
    created_at = _created()
    updated_at = _updated()
    __table_args__ = (
        CheckConstraint(
            "state IN ('pending','claimed','failed','published','dead_letter')",
            name="ck_outbox_event_state",
        ),
        CheckConstraint("schema_version > 0", name="ck_outbox_schema_version"),
        CheckConstraint("attempts >= 0", name="ck_outbox_attempts"),
        Index("ix_outbox_claimable", "state", "available_at", "created_at"),
        Index("ix_outbox_aggregate", "aggregate_type", "aggregate_id"),
    )


class DeviceRow(Base):
    __tablename__ = "devices"
    id = _id()
    user_id: Mapped[str] = mapped_column(UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    platform: Mapped[str] = mapped_column(String(16), nullable=False)
    push_token_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    locale: Mapped[str] = mapped_column(String(16), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    created_at = _created()
    updated_at = _updated()
    __table_args__ = (UniqueConstraint("platform", "push_token_ref", name="uq_device_push_ref"),)


class LegalAcceptanceRow(Base):
    __tablename__ = "legal_acceptances"
    id = _id()
    user_id: Mapped[str] = mapped_column(UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    document: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(UTC, nullable=False)
    ip_hash: Mapped[str | None] = mapped_column(String(128))
    __table_args__ = (UniqueConstraint("user_id", "document", "version", name="uq_legal_acceptance"),)


class PanchangDayRow(Base):
    __tablename__ = "panchang_days"
    id = _id()
    date: Mapped[DateValue] = mapped_column(Date, nullable=False)
    grid_lat: Mapped[Decimal] = mapped_column(Numeric(9, 4), nullable=False)
    grid_lon: Mapped[Decimal] = mapped_column(Numeric(9, 4), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    ayanamsa: Mapped[str] = mapped_column(String(32), nullable=False)
    scheme: Mapped[str] = mapped_column(String(32), nullable=False)
    engine_version: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False)
    created_at = _created()
    updated_at = _updated()
    __table_args__ = (
        UniqueConstraint("date", "grid_lat", "grid_lon", "timezone", "ayanamsa", "scheme", "engine_version", name="uq_panchang_cache_key"),
        Index("ix_panchang_day_grid", "date", "grid_lat", "grid_lon"),
    )


class FestivalRuleRow(Base):
    __tablename__ = "festival_rules"
    id = _id()
    identifier: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    rule_json: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False)
    scheme: Mapped[str] = mapped_column(String(32), nullable=False)
    regions: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    state: Mapped[str] = mapped_column(String(16), nullable=False, server_default="draft")
    created_at = _created()
    updated_at = _updated()
    __table_args__ = (UniqueConstraint("identifier", "version", name="uq_festival_rule_version"),)


class FestivalOccurrenceRow(Base):
    __tablename__ = "festival_occurrences"
    id = _id()
    rule_id: Mapped[str] = mapped_column(UUID, ForeignKey("festival_rules.id"), nullable=False)
    rule_version: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[DateValue] = mapped_column(Date, nullable=False)
    grid_lat: Mapped[Decimal] = mapped_column(Numeric(9, 4), nullable=False)
    grid_lon: Mapped[Decimal] = mapped_column(Numeric(9, 4), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    anchor_utc: Mapped[datetime] = mapped_column(UTC, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        UniqueConstraint("rule_id", "rule_version", "date", "grid_lat", "grid_lon", name="uq_festival_occurrence"),
        Index("ix_festival_occurrence_date_grid", "date", "grid_lat", "grid_lon"),
    )


class ContentVersionRow(Base):
    __tablename__ = "content_versions"
    id = _id()
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(UUID, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    author_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, server_default="draft")
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    diff: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict)
    created_at = _created()
    __table_args__ = (UniqueConstraint("entity_type", "entity_id", "version", name="uq_content_version"),)


class FestivalContentRow(Base):
    __tablename__ = "festival_content"
    id = _id()
    festival_id: Mapped[str] = mapped_column(UUID, ForeignKey("festival_rules.id"), nullable=False)
    festival_version: Mapped[int] = mapped_column(Integer, nullable=False)
    locale: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    puja: Mapped[str | None] = mapped_column(Text)
    katha: Mapped[str | None] = mapped_column(Text)
    samagri: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    source_attribution: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, server_default="draft")
    created_at = _created()
    updated_at = _updated()
    __table_args__ = (UniqueConstraint("festival_id", "festival_version", "locale", name="uq_festival_content_locale"),)


class ContentFlagRow(Base):
    __tablename__ = "content_flags"
    id = _id()
    content_id: Mapped[str] = mapped_column(UUID, ForeignKey("festival_content.id"), nullable=False)
    content_version: Mapped[int] = mapped_column(Integer, nullable=False)
    reporter_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, server_default="open")
    resolution: Mapped[str | None] = mapped_column(Text)
    created_at = _created()


class VratTypeRow(Base):
    __tablename__ = "vrat_types"
    id = _id()
    identifier: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    recurrence_rule: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False)
    content_ref: Mapped[str | None] = mapped_column(UUID)
    created_at = _created()
    updated_at = _updated()


class NoteRow(Base):
    __tablename__ = "notes"
    id = _id()
    owner_user_id: Mapped[str] = mapped_column(UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    family_group_id: Mapped[str | None] = mapped_column(UUID, ForeignKey("family_groups.id", ondelete="SET NULL"))
    date_ref: Mapped[DateValue | None] = mapped_column(Date)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_at = _created()
    updated_at = _updated()
    __table_args__ = (Index("ix_notes_owner_date", "owner_user_id", "date_ref"),)


class BookmarkRow(Base):
    __tablename__ = "bookmarks"
    id = _id()
    user_id: Mapped[str] = mapped_column(UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(UUID, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at = _created()
    __table_args__ = (UniqueConstraint("user_id", "target_type", "target_id", "category", name="uq_bookmark_target"),)


class ReminderRow(Base):
    __tablename__ = "reminders"
    id = _id()
    user_id: Mapped[str] = mapped_column(UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    recurrence_spec: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False)
    location_id: Mapped[str | None] = mapped_column(UUID, ForeignKey("locations.id", ondelete="SET NULL"))
    next_fire_at: Mapped[datetime | None] = mapped_column(UTC)
    fire_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    created_at = _created()
    updated_at = _updated()
    __table_args__ = (Index("ix_reminders_active_next_fire", "active", "next_fire_at"),)


class ReminderOccurrenceRow(Base):
    __tablename__ = "reminder_occurrences"
    id = _id()
    reminder_id: Mapped[str] = mapped_column(UUID, ForeignKey("reminders.id", ondelete="CASCADE"), nullable=False)
    occurrence_key: Mapped[str] = mapped_column(String(255), nullable=False)
    fire_at: Mapped[datetime] = mapped_column(UTC, nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, server_default="pending")
    __table_args__ = (UniqueConstraint("reminder_id", "occurrence_key", name="uq_reminder_occurrence"),)


class VratRecordRow(Base):
    __tablename__ = "vrat_records"
    id = _id()
    user_id: Mapped[str] = mapped_column(UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    vrat_type_id: Mapped[str] = mapped_column(UUID, ForeignKey("vrat_types.id"), nullable=False)
    occurrence_ref: Mapped[str | None] = mapped_column(UUID)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="planned")
    sankalp: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at = _created()
    updated_at = _updated()


class PlannerRequestRow(Base):
    __tablename__ = "planner_requests"
    id = _id()
    user_id: Mapped[str] = mapped_column(UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    start_date: Mapped[DateValue] = mapped_column(Date, nullable=False)
    end_date: Mapped[DateValue] = mapped_column(Date, nullable=False)
    location_id: Mapped[str | None] = mapped_column(UUID, ForeignKey("locations.id", ondelete="SET NULL"))
    preferences: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict)
    created_at = _created()
    __table_args__ = (CheckConstraint("end_date >= start_date", name="ck_planner_date_range"),)


class CalendarJobRow(Base):
    __tablename__ = "calendar_jobs"
    id = _id()
    user_id: Mapped[str] = mapped_column(UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    template: Mapped[str] = mapped_column(String(64), nullable=False)
    start_date: Mapped[DateValue] = mapped_column(Date, nullable=False)
    end_date: Mapped[DateValue] = mapped_column(Date, nullable=False)
    options: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="queued")
    object_ref: Mapped[str | None] = mapped_column(String(512))
    created_at = _created()
    updated_at = _updated()


class SubscriptionRow(Base):
    __tablename__ = "subscriptions"
    id = _id()
    user_id: Mapped[str] = mapped_column(UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tier: Mapped[str] = mapped_column(String(16), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(UTC)
    created_at = _created()
    updated_at = _updated()
    __table_args__ = (
        UniqueConstraint("source", "provider_ref", name="uq_subscription_provider_ref"),
        Index("uq_active_subscription_user", "user_id", unique=True, sqlite_where=text("status = 'active'"), postgresql_where=text("status = 'active'")),
    )


class ProviderAccountRow(Base):
    __tablename__ = "provider_accounts"
    id = _id()
    user_id: Mapped[str] = mapped_column(UUID, ForeignKey("users.id"), nullable=False)
    account_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    stripe_account_ref: Mapped[str | None] = mapped_column(String(255), unique=True)
    kyc_status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending")
    standing: Mapped[str] = mapped_column(String(32), nullable=False, server_default="good")
    created_at = _created()
    updated_at = _updated()
    __table_args__ = (UniqueConstraint("user_id", "account_type", name="uq_provider_user_role"),)


class VerificationRecordRow(Base):
    __tablename__ = "verification_records"
    id = _id()
    provider_id: Mapped[str] = mapped_column(UUID, ForeignKey("provider_accounts.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    vendor: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    vault_ref_id: Mapped[str | None] = mapped_column(UUID, ForeignKey("vault_refs.id"))
    expires_at: Mapped[datetime | None] = mapped_column(UTC)
    created_at = _created()
    __table_args__ = (UniqueConstraint("provider_id", "kind", "vendor", name="uq_verification_provider_kind"),)


class CommissionPolicyRow(Base):
    __tablename__ = "commission_policies"
    id = _id()
    marketplace: Mapped[str] = mapped_column(String(32), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(7, 6), nullable=False)
    pass_through_rules: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict)
    effective_from: Mapped[datetime] = mapped_column(UTC, nullable=False)
    created_at = _created()
    __table_args__ = (CheckConstraint("rate >= 0 AND rate <= 1", name="ck_commission_rate"),)


class TaxRecordRow(Base):
    __tablename__ = "tax_records"
    id = _id()
    aggregate_type: Mapped[str] = mapped_column(String(32), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(UUID, nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_ref: Mapped[str | None] = mapped_column(String(255))
    amount_minor: Mapped[int] = mapped_column(MONEY, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at = _created()
    __table_args__ = (CheckConstraint("amount_minor >= 0", name="ck_tax_nonnegative"), CheckConstraint("length(currency) = 3", name="ck_tax_currency"))


class PaymentRow(Base):
    __tablename__ = "payments"
    id = _id()
    aggregate_type: Mapped[str] = mapped_column(String(32), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(UUID, nullable=False)
    intent_ref: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    amount_minor: Mapped[int] = mapped_column(MONEY, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    captured_at: Mapped[datetime | None] = mapped_column(UTC)
    created_at = _created()
    __table_args__ = (CheckConstraint("amount_minor >= 0", name="ck_payment_nonnegative"), CheckConstraint("length(currency) = 3", name="ck_payment_currency"))


class PayoutRow(Base):
    __tablename__ = "payouts"
    id = _id()
    provider_id: Mapped[str] = mapped_column(UUID, ForeignKey("provider_accounts.id"), nullable=False)
    aggregate_ref: Mapped[str] = mapped_column(UUID, nullable=False)
    amount_minor: Mapped[int] = mapped_column(MONEY, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    hold_until: Mapped[datetime | None] = mapped_column(UTC)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at = _created()
    __table_args__ = (CheckConstraint("amount_minor >= 0", name="ck_payout_nonnegative"), CheckConstraint("length(currency) = 3", name="ck_payout_currency"))


class RefundRow(Base):
    __tablename__ = "refunds"
    id = _id()
    aggregate_ref: Mapped[str] = mapped_column(UUID, nullable=False)
    amount_minor: Mapped[int] = mapped_column(MONEY, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    policy_tier: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_ref: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at = _created()
    __table_args__ = (CheckConstraint("amount_minor >= 0", name="ck_refund_nonnegative"),)


class DisputeRow(Base):
    __tablename__ = "disputes"
    id = _id()
    aggregate_ref: Mapped[str] = mapped_column(UUID, nullable=False)
    raised_by: Mapped[str] = mapped_column(UUID, ForeignKey("users.id"), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_refs: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    resolution: Mapped[str | None] = mapped_column(Text)
    created_at = _created()
    updated_at = _updated()


class LedgerJournalRow(Base):
    __tablename__ = "ledger_journals"
    id = _id()
    aggregate_ref: Mapped[str] = mapped_column(UUID, nullable=False)
    external_ref: Mapped[str | None] = mapped_column(String(255), unique=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    debit_total_minor: Mapped[int] = mapped_column(MONEY, nullable=False, server_default="0")
    credit_total_minor: Mapped[int] = mapped_column(MONEY, nullable=False, server_default="0")
    created_at = _created()
    __table_args__ = (
        CheckConstraint("debit_total_minor = credit_total_minor", name="ck_ledger_journal_balanced"),
        CheckConstraint("debit_total_minor >= 0 AND credit_total_minor >= 0", name="ck_ledger_journal_nonnegative"),
        CheckConstraint("length(currency) = 3", name="ck_ledger_journal_currency"),
        Index("ix_ledger_journal_aggregate", "aggregate_ref"),
    )


class LedgerEntryRow(Base):
    __tablename__ = "ledger_entries"
    id = _id()
    journal_id: Mapped[str] = mapped_column(UUID, ForeignKey("ledger_journals.id", ondelete="CASCADE"), nullable=False)
    account: Mapped[str] = mapped_column(String(255), nullable=False)
    debit_minor: Mapped[int] = mapped_column(MONEY, nullable=False, server_default="0")
    credit_minor: Mapped[int] = mapped_column(MONEY, nullable=False, server_default="0")
    created_at = _created()
    __table_args__ = (
        CheckConstraint("debit_minor >= 0 AND credit_minor >= 0", name="ck_ledger_entry_nonnegative"),
        CheckConstraint("(debit_minor = 0) <> (credit_minor = 0)", name="ck_ledger_entry_one_side"),
        Index("ix_ledger_entries_journal", "journal_id"),
    )


class WebhookReceiptRow(Base):
    __tablename__ = "webhook_receipts"
    id = _id()
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    external_event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(UTC)
    created_at = _created()
    __table_args__ = (UniqueConstraint("provider", "external_event_id", name="uq_webhook_provider_event"),)


class PanditRow(Base):
    __tablename__ = "pandits"
    provider_id: Mapped[str] = mapped_column(UUID, ForeignKey("provider_accounts.id", ondelete="CASCADE"), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    bio: Mapped[str] = mapped_column(Text, nullable=False, default="")
    base_location_id: Mapped[str | None] = mapped_column(UUID, ForeignKey("locations.id"))
    languages: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    traditions: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    approval: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending")
    created_at = _created()
    updated_at = _updated()
    __table_args__ = (Index("ix_pandits_base_location", "base_location_id"),)


class ServiceTypeRow(Base):
    __tablename__ = "service_types"
    id = _id()
    name: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    festival_refs: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    muhurat_types: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    default_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at = _created()
    __table_args__ = (CheckConstraint("default_duration_minutes > 0", name="ck_service_duration"),)


class PanditServiceRow(Base):
    __tablename__ = "pandit_services"
    id = _id()
    pandit_id: Mapped[str] = mapped_column(UUID, ForeignKey("pandits.provider_id", ondelete="CASCADE"), nullable=False)
    service_type_id: Mapped[str] = mapped_column(UUID, ForeignKey("service_types.id"), nullable=False)
    modes: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    base_price_minor: Mapped[int] = mapped_column(MONEY, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    samagri: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    created_at = _created()
    updated_at = _updated()
    __table_args__ = (CheckConstraint("duration_minutes > 0", name="ck_pandit_service_duration"), CheckConstraint("base_price_minor >= 0", name="ck_pandit_service_price"), CheckConstraint("length(currency) = 3", name="ck_pandit_service_currency"))


class SamagriListRow(Base):
    """CMS mapping from a festival/service item to an optional Shopify variant."""

    __tablename__ = "samagri_lists"
    id = _id()
    festival_ref: Mapped[str | None] = mapped_column(UUID, ForeignKey("festival_rules.id"))
    service_type_id: Mapped[str | None] = mapped_column(UUID, ForeignKey("service_types.id"))
    item_name: Mapped[str] = mapped_column(String(200), nullable=False)
    shopify_variant_id: Mapped[str | None] = mapped_column(String(255))
    created_at = _created()
    __table_args__ = (
        CheckConstraint("festival_ref IS NOT NULL OR service_type_id IS NOT NULL", name="ck_samagri_parent"),
        UniqueConstraint("festival_ref", "service_type_id", "item_name", name="uq_samagri_item"),
    )


class TravelPolicyRow(Base):
    __tablename__ = "travel_policies"
    pandit_id: Mapped[str] = mapped_column(UUID, ForeignKey("pandits.provider_id", ondelete="CASCADE"), primary_key=True)
    radius_miles: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    fee_model: Mapped[str] = mapped_column(String(32), nullable=False)
    bands: Mapped[list[dict[str, Any]]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    pickup_required: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    __table_args__ = (CheckConstraint("radius_miles >= 0 AND radius_miles <= 100", name="ck_travel_radius"),)


class AvailabilityRuleRow(Base):
    __tablename__ = "availability_rules"
    id = _id()
    pandit_id: Mapped[str] = mapped_column(UUID, ForeignKey("pandits.provider_id", ondelete="CASCADE"), nullable=False)
    weekly_hours: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False)
    lead_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    buffer_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    acceptance_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at = _created()


class AvailabilityBlackoutRow(Base):
    __tablename__ = "availability_blackouts"
    id = _id()
    pandit_id: Mapped[str] = mapped_column(UUID, ForeignKey("pandits.provider_id", ondelete="CASCADE"), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(UTC, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(UTC, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (CheckConstraint("ends_at > starts_at", name="ck_blackout_range"), Index("ix_blackouts_pandit_time", "pandit_id", "starts_at", "ends_at"))


class BookingRow(Base):
    __tablename__ = "bookings"
    id = _id()
    patron_id: Mapped[str] = mapped_column(UUID, ForeignKey("users.id"), nullable=False)
    pandit_id: Mapped[str] = mapped_column(UUID, ForeignKey("pandits.provider_id"), nullable=False)
    service_id: Mapped[str] = mapped_column(UUID, ForeignKey("pandit_services.id"), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(UTC, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(UTC, nullable=False)
    slot_range: Mapped[str | None] = mapped_column(TimestampRange())
    state: Mapped[str] = mapped_column(String(32), nullable=False, server_default="requested")
    quote_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False)
    policy_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False)
    address_vault_ref_id: Mapped[str | None] = mapped_column(UUID, ForeignKey("vault_refs.id"))
    created_at = _created()
    updated_at = _updated()
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="ck_booking_range"),
        Index("ix_bookings_pandit_time_state", "pandit_id", "starts_at", "ends_at", "state"),
    )


class BookingEventRow(Base):
    __tablename__ = "booking_events"
    id = _id()
    booking_id: Mapped[str] = mapped_column(UUID, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    from_state: Mapped[str | None] = mapped_column(String(32))
    to_state: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(UTC, nullable=False)
    __table_args__ = (Index("ix_booking_events_booking_time", "booking_id", "occurred_at"),)


class BookingHoldRow(Base):
    __tablename__ = "booking_holds"
    id = _id()
    booking_id: Mapped[str] = mapped_column(UUID, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    slot_range: Mapped[str] = mapped_column(TimestampRange(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UTC, nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, server_default="active")
    created_at = _created()
    __table_args__ = (UniqueConstraint("booking_id", "state", name="uq_active_booking_hold"), Index("ix_booking_holds_expiry", "state", "expires_at"))


class ReviewRow(Base):
    __tablename__ = "reviews"
    id = _id()
    booking_id: Mapped[str] = mapped_column(UUID, ForeignKey("bookings.id"), nullable=False)
    author_user_id: Mapped[str] = mapped_column(UUID, ForeignKey("users.id"), nullable=False)
    author_role: Mapped[str] = mapped_column(String(16), nullable=False)
    stars: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    moderation: Mapped[str] = mapped_column(String(16), nullable=False, server_default="pending")
    reveal_at: Mapped[datetime | None] = mapped_column(UTC)
    created_at = _created()
    __table_args__ = (UniqueConstraint("booking_id", "author_role", name="uq_review_booking_side"), CheckConstraint("stars BETWEEN 1 AND 5", name="ck_review_stars"))


class ConversationRow(Base):
    __tablename__ = "conversations"
    id = _id()
    booking_id: Mapped[str | None] = mapped_column(UUID, ForeignKey("bookings.id"))
    enquiry_ref: Mapped[str | None] = mapped_column(UUID)
    participants: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    state: Mapped[str] = mapped_column(String(16), nullable=False, server_default="open")
    created_at = _created()


class MessageRow(Base):
    __tablename__ = "messages"
    id = _id()
    conversation_id: Mapped[str] = mapped_column(UUID, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    sender_id: Mapped[str] = mapped_column(UUID, ForeignKey("users.id"), nullable=False)
    masked_body: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_ref: Mapped[str | None] = mapped_column(String(512))
    flags: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    created_at = _created()


class VideoSessionRow(Base):
    __tablename__ = "video_sessions"
    id = _id()
    booking_id: Mapped[str] = mapped_column(UUID, ForeignKey("bookings.id"), nullable=False, unique=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    room_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    join_log: Mapped[list[dict[str, Any]]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    recording_ref: Mapped[str | None] = mapped_column(String(512))
    created_at = _created()


class SellerRow(Base):
    __tablename__ = "sellers"
    provider_id: Mapped[str] = mapped_column(UUID, ForeignKey("provider_accounts.id", ondelete="CASCADE"), primary_key=True)
    shop_name: Mapped[str] = mapped_column(String(200), nullable=False)
    approval: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending")
    standing: Mapped[str] = mapped_column(String(32), nullable=False, server_default="good")
    created_at = _created()
    updated_at = _updated()


class ProductRefRow(Base):
    __tablename__ = "product_refs"
    id = _id()
    shopify_product_id: Mapped[str] = mapped_column(String(255), nullable=False)
    shopify_variant_id: Mapped[str] = mapped_column(String(255), nullable=False)
    seller_id: Mapped[str] = mapped_column(UUID, ForeignKey("sellers.provider_id"), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    festival_refs: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    product_type: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at = _created()
    __table_args__ = (UniqueConstraint("shopify_product_id", "shopify_variant_id", name="uq_shopify_product_variant"), Index("ix_product_refs_seller", "seller_id"))


class OrderRefRow(Base):
    __tablename__ = "order_refs"
    id = _id()
    shopify_order_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    buyer_id: Mapped[str] = mapped_column(UUID, ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    totals_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False)
    tax_ref: Mapped[str | None] = mapped_column(String(255))
    created_at = _created()
    updated_at = _updated()
    __table_args__ = (Index("ix_order_refs_buyer", "buyer_id"),)


class OrderSellerSplitRow(Base):
    __tablename__ = "order_seller_splits"
    id = _id()
    order_id: Mapped[str] = mapped_column(UUID, ForeignKey("order_refs.id", ondelete="CASCADE"), nullable=False)
    seller_id: Mapped[str] = mapped_column(UUID, ForeignKey("sellers.provider_id"), nullable=False)
    line_refs: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    commission_minor: Mapped[int] = mapped_column(MONEY, nullable=False)
    payout_status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at = _created()
    __table_args__ = (UniqueConstraint("order_id", "seller_id", name="uq_order_seller_split"), CheckConstraint("commission_minor >= 0", name="ck_split_commission"))


class FulfillmentRow(Base):
    __tablename__ = "fulfillments"
    id = _id()
    split_id: Mapped[str] = mapped_column(UUID, ForeignKey("order_seller_splits.id", ondelete="CASCADE"), nullable=False)
    carrier: Mapped[str | None] = mapped_column(String(64))
    tracking: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    shipped_at: Mapped[datetime | None] = mapped_column(UTC)
    delivered_at: Mapped[datetime | None] = mapped_column(UTC)
    created_at = _created()


class ReturnRequestRow(Base):
    __tablename__ = "return_requests"
    id = _id()
    order_id: Mapped[str] = mapped_column(UUID, ForeignKey("order_refs.id"), nullable=False)
    line_refs: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    refund_ref: Mapped[str | None] = mapped_column(String(255))
    created_at = _created()


class ProductReviewRow(Base):
    __tablename__ = "product_reviews"
    id = _id()
    product_id: Mapped[str] = mapped_column(UUID, ForeignKey("product_refs.id"), nullable=False)
    buyer_id: Mapped[str] = mapped_column(UUID, ForeignKey("users.id"), nullable=False)
    order_ref_id: Mapped[str] = mapped_column(UUID, ForeignKey("order_refs.id"), nullable=False)
    stars: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    moderation: Mapped[str] = mapped_column(String(16), nullable=False, server_default="pending")
    created_at = _created()
    __table_args__ = (UniqueConstraint("product_id", "buyer_id", "order_ref_id", name="uq_product_review_purchase"), CheckConstraint("stars BETWEEN 1 AND 5", name="ck_product_review_stars"))


# SQLite has no range/exclusion constraint.  PostgreSQL derives the authoritative
# range from the UTC start/end instants before applying the active-slot exclusion;
# the starts/ends check and overlap triggers remain portable and are exercised by
# the local model tests.
event.listen(
    BookingRow.__table__,
    "after_create",
    DDL(
        """
        CREATE OR REPLACE FUNCTION set_booking_slot_range() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            NEW.slot_range := tstzrange(NEW.starts_at, NEW.ends_at, '[)');
            RETURN NEW;
        END;
        $$;
        """
    ).execute_if(dialect="postgresql"),
)
event.listen(
    BookingRow.__table__,
    "after_create",
    DDL(
        """
        CREATE TRIGGER set_booking_slot_range_before_write
        BEFORE INSERT OR UPDATE OF starts_at, ends_at ON bookings
        FOR EACH ROW EXECUTE FUNCTION set_booking_slot_range()
        """
    ).execute_if(dialect="postgresql"),
)
event.listen(
    BookingRow.__table__,
    "after_create",
    DDL(
        "ALTER TABLE bookings ADD CONSTRAINT ex_bookings_pandit_slot "
        "EXCLUDE USING gist (pandit_id WITH =, slot_range WITH &&) "
        "WHERE (state IN ('requested','confirmed','reschedule_pending','in_progress'))"
    ).execute_if(dialect="postgresql"),
)
event.listen(
    BookingRow.__table__,
    "after_create",
    DDL(
        "CREATE TRIGGER prevent_booking_overlap_insert "
        "BEFORE INSERT ON bookings "
        "WHEN NEW.state IN ('requested','confirmed','reschedule_pending','in_progress') "
        "AND EXISTS (SELECT 1 FROM bookings b WHERE b.pandit_id = NEW.pandit_id "
        "AND b.state IN ('requested','confirmed','reschedule_pending','in_progress') "
        "AND NEW.starts_at < b.ends_at AND NEW.ends_at > b.starts_at) "
        "BEGIN SELECT RAISE(ABORT, 'booking slot overlaps an active booking'); END"
    ).execute_if(dialect="sqlite"),
)
event.listen(
    BookingRow.__table__,
    "after_create",
    DDL(
        "CREATE TRIGGER prevent_booking_overlap_update "
        "BEFORE UPDATE OF pandit_id, starts_at, ends_at, state ON bookings "
        "WHEN NEW.state IN ('requested','confirmed','reschedule_pending','in_progress') "
        "AND EXISTS (SELECT 1 FROM bookings b WHERE b.id <> NEW.id "
        "AND b.pandit_id = NEW.pandit_id "
        "AND b.state IN ('requested','confirmed','reschedule_pending','in_progress') "
        "AND NEW.starts_at < b.ends_at AND NEW.ends_at > b.starts_at) "
        "BEGIN SELECT RAISE(ABORT, 'booking slot overlaps an active booking'); END"
    ).execute_if(dialect="sqlite"),
)


__all__ = [name for name in globals() if name.endswith("Row")]
