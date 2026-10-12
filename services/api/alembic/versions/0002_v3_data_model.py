"""v3.0 data-model foundation.

This is an additive revision after the legacy temple migration.  The table list is
created from the declarative metadata in dependency order, which keeps foreign-key
ordering in one place and makes the SQLite migration smoke test equivalent to the
PostgreSQL path.  Outbox processing and Vault access behavior are intentionally not
part of this revision (S0-05).

Revision ID: 0002_v3_data_model
Revises: 0001_initial_temple
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import text

from alembic import op
from api.db import Base
from api.db import models as _models  # noqa: F401  # register all metadata tables

# revision identifiers, used by Alembic.
revision: str = "0002_v3_data_model"
down_revision: str | None = "0001_initial_temple"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# A historical revision must never silently pick up a table introduced in a
# later model. Keep the v3.0 foundation's table membership frozen here; 0003
# owns outbox/idempotency, and later additions need their own revision.
_V3_TABLES = frozenset(
    """users user_preferences locations family_groups family_memberships vault_refs
    vault_access_log devices legal_acceptances panchang_days festival_rules
    festival_occurrences festival_content content_versions content_flags vrat_types
    notes bookmarks reminders reminder_occurrences vrat_records planner_requests
    calendar_jobs subscriptions provider_accounts verification_records
    commission_policies tax_records payments payouts refunds disputes ledger_journals
    ledger_entries webhook_receipts pandits service_types pandit_services
    samagri_lists travel_policies availability_rules availability_blackouts bookings
    booking_events booking_holds reviews conversations messages video_sessions sellers
    product_refs order_refs order_seller_splits fulfillments return_requests
    product_reviews""".split()
)


def upgrade() -> None:
    bind = op.get_bind()
    # Geography and the booking exclusion index are production-only extensions.
    # SQLite uses the explicit type fallbacks in api.db.v3_models and skips these.
    if bind.dialect.name == "postgresql":
        bind.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        bind.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))

    tables = [table for table in Base.metadata.sorted_tables if table.name in _V3_TABLES]
    Base.metadata.create_all(bind=bind, tables=tables, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    tables = [table for table in reversed(Base.metadata.sorted_tables) if table.name in _V3_TABLES]
    Base.metadata.drop_all(bind=bind, tables=tables, checkfirst=True)
