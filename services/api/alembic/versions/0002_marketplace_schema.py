"""marketplace schema + no-double-booking constraint (F2)

Creates every marketplace table from the data model (Architecture v1.2 §3):
Pandit, ServiceType, PanditService, TravelPolicy, Availability, VerificationRecord,
Booking, BookingEvent, Payment, Payout, Refund, Review, Conversation, Message,
VideoSession, Dispute — plus the indexes each needs.

The integrity centrepiece is the **no-double-booking** guarantee (north-star #6): a
Postgres exclusion constraint that rejects two overlapping bookings for the same
``pandit_id`` while either is in an active/confirmed state. It is implemented as an
``ExcludeConstraint`` over ``tstzrange(start_time, end_time)`` with ``=`` on
``pandit_id`` and ``&&`` on the range, using a GiST index — which requires the
``btree_gist`` extension (created here). The constraint is **partial**: it only applies
to the active statuses (requested/confirmed/reschedule_pending/in_progress/disputed),
so a cancelled or completed booking frees the slot.

All of the above is **Postgres-only**. On SQLite (the local test engine) this whole
migration is skipped for schema creation — the test suite builds its schema via
``Base.metadata.create_all``, which sees the ORM models but *not* the ExcludeConstraint
(that construct lives only here), so SQLite never chokes on it.

Revision ID: 0002_marketplace_schema
Revises: 0001_initial_temple
Create Date: 2026-07-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_marketplace_schema"
down_revision: str | None = "0001_initial_temple"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# JSONB on Postgres, JSON elsewhere (matches api.db.base.JSON_VARIANT).
JSON_VARIANT = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

# Money precision, mirrored from the ORM.
MONEY = sa.Numeric(12, 2)

# The statuses that hold a slot — mirrors ACTIVE_BOOKING_STATUSES in the ORM. Kept as
# a literal here so the migration is self-contained (Alembic best practice: no runtime
# app imports for structural DDL).
ACTIVE_BOOKING_STATUSES = (
    "requested",
    "confirmed",
    "reschedule_pending",
    "in_progress",
    "disputed",
)

# Name of the exclusion constraint — referenced by tests and by downgrade().
OVERLAP_CONSTRAINT = "no_double_booking_overlap"


def _active_status_predicate() -> str:
    quoted = ", ".join(f"'{s}'" for s in ACTIVE_BOOKING_STATUSES)
    return f"status IN ({quoted})"


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # ── Provider (Pandit) profile & catalogue ─────────────────────────────────
    op.create_table(
        "pandits",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("bio", sa.String(), nullable=True),
        sa.Column("base_location_id", sa.String(), nullable=True),
        sa.Column("languages", JSON_VARIANT, nullable=False),
        sa.Column("tradition", sa.String(), nullable=True),
        sa.Column("experience_years", sa.Integer(), nullable=True),
        sa.Column("verification_status", sa.String(), nullable=False, server_default="unverified"),
        sa.Column("rating_agg", sa.Numeric(3, 2), nullable=True),
        sa.Column("rating_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("standing_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("payout_account_ref", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_pandits_user_id", "pandits", ["user_id"])

    op.create_table(
        "service_types",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("festival_ref", sa.String(), nullable=True),
        sa.Column("muhurat_event_ref", sa.String(), nullable=True),
        sa.Column("taxonomy_tags", JSON_VARIANT, nullable=False),
    )
    op.create_index("ix_service_types_category", "service_types", ["category"])

    op.create_table(
        "pandit_services",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "pandit_id",
            sa.String(),
            sa.ForeignKey("pandits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "service_type_id",
            sa.String(),
            sa.ForeignKey("service_types.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("modes", JSON_VARIANT, nullable=False),
        sa.Column("duration_min", sa.Integer(), nullable=False),
        sa.Column("base_price", MONEY, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("samagri_option", sa.String(), nullable=False, server_default="none"),
        sa.Column("samagri_price", MONEY, nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_pandit_services_pandit_id", "pandit_services", ["pandit_id"])
    op.create_index("ix_pandit_services_service_type_id", "pandit_services", ["service_type_id"])

    op.create_table(
        "travel_policies",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "pandit_id",
            sa.String(),
            sa.ForeignKey("pandits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("will_travel", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("max_radius_miles", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fee_model", sa.String(), nullable=False, server_default="flat"),
        sa.Column("fee_config", JSON_VARIANT, nullable=False),
        sa.Column("requires_pickup", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_travel_policies_pandit_id", "travel_policies", ["pandit_id"], unique=True)

    op.create_table(
        "availabilities",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "pandit_id",
            sa.String(),
            sa.ForeignKey("pandits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rules", JSON_VARIANT, nullable=False),
        sa.Column("blackout_dates", JSON_VARIANT, nullable=False),
        sa.Column("lead_time_min", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("buffer_min", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accept_mode", sa.String(), nullable=False, server_default="manual"),
    )
    op.create_index("ix_availabilities_pandit_id", "availabilities", ["pandit_id"], unique=True)

    op.create_table(
        "verification_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "pandit_id",
            sa.String(),
            sa.ForeignKey("pandits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("id_status", sa.String(), nullable=False, server_default="unverified"),
        sa.Column("bg_check_status", sa.String(), nullable=False, server_default="unverified"),
        sa.Column("address_status", sa.String(), nullable=False, server_default="unverified"),
        sa.Column("vault_refs", JSON_VARIANT, nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_verification_records_pandit_id",
        "verification_records",
        ["pandit_id"],
        unique=True,
    )

    # ── Bookings & lifecycle ──────────────────────────────────────────────────
    op.create_table(
        "bookings",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("patron_user_id", sa.String(), nullable=False),
        sa.Column(
            "pandit_id",
            sa.String(),
            sa.ForeignKey("pandits.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "pandit_service_id",
            sa.String(),
            sa.ForeignKey("pandit_services.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("mode", sa.String(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tz", sa.String(), nullable=False),
        sa.Column("address_ref", sa.String(), nullable=True),
        sa.Column("samagri_chosen", sa.String(), nullable=False, server_default="none"),
        sa.Column("status", sa.String(), nullable=False, server_default="requested"),
        sa.Column("price_breakdown", JSON_VARIANT, nullable=False),
        # policySnapshot — immutable per-booking policy/fee terms (JSONB on Postgres).
        sa.Column("policy_snapshot", JSON_VARIANT, nullable=False),
        sa.Column("muhurat_ref", sa.String(), nullable=True),
        sa.Column("sankalp", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_bookings_patron_user_id", "bookings", ["patron_user_id"])
    op.create_index("ix_bookings_pandit_id", "bookings", ["pandit_id"])
    op.create_index("ix_bookings_pandit_service_id", "bookings", ["pandit_service_id"])
    op.create_index("ix_bookings_status", "bookings", ["status"])
    op.create_index("ix_bookings_pandit_start", "bookings", ["pandit_id", "start_time"])

    # ── The no-double-booking exclusion constraint (Postgres-only) ────────────
    # Requires btree_gist so a plain-equality column (pandit_id) can share a GiST
    # index with the range-overlap operator on tstzrange(start_time, end_time).
    if is_postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
        op.execute(
            f"""
            ALTER TABLE bookings
            ADD CONSTRAINT {OVERLAP_CONSTRAINT}
            EXCLUDE USING gist (
                pandit_id WITH =,
                tstzrange(start_time, end_time) WITH &&
            )
            WHERE ({_active_status_predicate()})
            """
        )

    op.create_table(
        "booking_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "booking_id",
            sa.String(),
            sa.ForeignKey("bookings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_state", sa.String(), nullable=True),
        sa.Column("to_state", sa.String(), nullable=False),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_booking_events_booking_id", "booking_events", ["booking_id"])

    # ── Money: payments, payouts, refunds ─────────────────────────────────────
    op.create_table(
        "payments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "booking_id",
            sa.String(),
            sa.ForeignKey("bookings.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("stripe_refs", JSON_VARIANT, nullable=False),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("commission", MONEY, nullable=False, server_default="0"),
        sa.Column("taxes", MONEY, nullable=False, server_default="0"),
        sa.Column("status", sa.String(), nullable=False, server_default="authorized"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_payments_booking_id", "payments", ["booking_id"], unique=True)
    op.create_index("ix_payments_status", "payments", ["status"])

    op.create_table(
        "payouts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "pandit_id",
            sa.String(),
            sa.ForeignKey("pandits.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("statement_ref", sa.String(), nullable=True),
        sa.Column("stripe_refs", JSON_VARIANT, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_payouts_pandit_id", "payouts", ["pandit_id"])
    op.create_index("ix_payouts_status", "payouts", ["status"])

    op.create_table(
        "refunds",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "booking_id",
            sa.String(),
            sa.ForeignKey("bookings.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("policy_tier", sa.String(), nullable=True),
        sa.Column("stripe_refs", JSON_VARIANT, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_refunds_booking_id", "refunds", ["booking_id"])

    # ── Reviews ────────────────────────────────────────────────────────────────
    op.create_table(
        "reviews",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "booking_id",
            sa.String(),
            sa.ForeignKey("bookings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("author_role", sa.String(), nullable=False),
        sa.Column("stars", sa.Integer(), nullable=False),
        sa.Column("body", sa.String(), nullable=True),
        sa.Column("moderation_state", sa.String(), nullable=False, server_default="pending"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("booking_id", "author_role", name="uq_review_booking_author"),
    )
    op.create_index("ix_reviews_booking_id", "reviews", ["booking_id"])
    op.create_index("ix_reviews_moderation_state", "reviews", ["moderation_state"])

    # ── Messaging ──────────────────────────────────────────────────────────────
    op.create_table(
        "conversations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "booking_id",
            sa.String(),
            sa.ForeignKey("bookings.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("participants", JSON_VARIANT, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_conversations_booking_id", "conversations", ["booking_id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.String(),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sender_user_id", sa.String(), nullable=False),
        sa.Column("body", sa.String(), nullable=True),
        sa.Column("attachment_ref", sa.String(), nullable=True),
        sa.Column("flags", JSON_VARIANT, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])

    # ── Live video (Phase 2) ──────────────────────────────────────────────────
    op.create_table(
        "video_sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "booking_id",
            sa.String(),
            sa.ForeignKey("bookings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(), nullable=True),
        sa.Column("join_window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("join_window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("join_log", JSON_VARIANT, nullable=False),
        sa.Column("recording_ref", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_video_sessions_booking_id", "video_sessions", ["booking_id"], unique=True)

    # ── Disputes ───────────────────────────────────────────────────────────────
    op.create_table(
        "disputes",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "booking_id",
            sa.String(),
            sa.ForeignKey("bookings.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("raised_by", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("evidence_refs", JSON_VARIANT, nullable=False),
        sa.Column("state", sa.String(), nullable=False, server_default="open"),
        sa.Column("resolution", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_disputes_booking_id", "disputes", ["booking_id"])
    op.create_index("ix_disputes_state", "disputes", ["state"])


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    op.drop_table("disputes")
    op.drop_table("video_sessions")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("reviews")
    op.drop_table("refunds")
    op.drop_table("payouts")
    op.drop_table("payments")
    op.drop_table("booking_events")

    if is_postgres:
        op.execute(f"ALTER TABLE bookings DROP CONSTRAINT IF EXISTS {OVERLAP_CONSTRAINT}")
    op.drop_table("bookings")

    op.drop_table("verification_records")
    op.drop_table("availabilities")
    op.drop_table("travel_policies")
    op.drop_table("pandit_services")
    op.drop_table("service_types")
    op.drop_table("pandits")

    # Leave btree_gist installed — it is a shared, harmless extension and other
    # objects may come to depend on it; dropping it on downgrade risks failures.
