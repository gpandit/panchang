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

from alembic import op
from sqlalchemy import text

from api.db import Base
from api.db import models as _models  # noqa: F401  # register all metadata tables

# revision identifiers, used by Alembic.
revision: str = "0002_v3_data_model"
down_revision: str | None = "0001_initial_temple"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_LEGACY_TABLES = {"temples", "temple_admin_accounts"}


def upgrade() -> None:
    bind = op.get_bind()
    # Geography and the booking exclusion index are production-only extensions.
    # SQLite uses the explicit type fallbacks in api.db.v3_models and skips these.
    if bind.dialect.name == "postgresql":
        bind.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        bind.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))

    tables = [
        table
        for table in Base.metadata.sorted_tables
        if table.name not in _LEGACY_TABLES
    ]
    Base.metadata.create_all(bind=bind, tables=tables, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    tables = [
        table
        for table in reversed(Base.metadata.sorted_tables)
        if table.name not in _LEGACY_TABLES
    ]
    Base.metadata.drop_all(bind=bind, tables=tables, checkfirst=True)
