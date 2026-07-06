"""sensitive vault tables (F3)

Creates the store-by-reference Sensitive Vault (Architecture v1.2 §15.1 /
north-star #7): sensitive artefacts (ID docs, background-check results, exact
addresses, payout accounts) are sealed at rest and addressed only by an opaque
ref. The marketplace tables from F2 already carry those refs as plain strings
(``bookings.address_ref``, ``verification_records.vault_refs``,
``pandits.payout_account_ref`` …); these two tables are where the sealed value
and its access audit trail actually live.

* ``vault_entries`` — one row per sealed value; ``id`` *is* the opaque ref token.
* ``vault_access_log`` — append-only audit: one row per raw-value read.

Both mirror the ORM in ``api.marketplace.vault``. They use no Postgres-specific
types (``LargeBinary`` → ``BYTEA`` on PG, ``BLOB`` on SQLite via SQLAlchemy), so
this migration is fully dialect-neutral — no sqlite/PG split needed.

Revision ID: 0003_vault_tables
Revises: 0002_marketplace_schema
Create Date: 2026-07-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_vault_tables"
down_revision: str | None = "0002_marketplace_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Sealed sensitive values, addressed by their opaque id (the ref token) ──
    op.create_table(
        "vault_entries",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("item_type", sa.String(), nullable=False, server_default="other"),
        sa.Column("sealed", sa.LargeBinary(), nullable=False),
        sa.Column("owner_ref", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_vault_entries_item_type", "vault_entries", ["item_type"])
    op.create_index("ix_vault_entries_owner_ref", "vault_entries", ["owner_ref"])

    # ── Append-only read audit trail (north-star #7) ──────────────────────────
    op.create_table(
        "vault_access_log",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "entry_id",
            sa.String(),
            sa.ForeignKey("vault_entries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("purpose", sa.String(), nullable=True),
        sa.Column("accessed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_vault_access_log_entry_id", "vault_access_log", ["entry_id"])


def downgrade() -> None:
    op.drop_table("vault_access_log")
    op.drop_table("vault_entries")
