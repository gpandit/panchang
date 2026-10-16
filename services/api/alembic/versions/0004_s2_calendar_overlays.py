"""Persist note tags used by the S2 calendar overlay APIs.

Revision ID: 0004_s2_calendar_overlays
Revises: 0003_s005_outbox_idempotency
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_s2_calendar_overlays"
down_revision: str | None = "0003_s005_outbox_idempotency"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 0002 builds fresh databases from the current metadata, so tags already
    # exists on a new install. Existing 0003 databases need the additive ALTER.
    bind = op.get_bind()
    if "tags" not in {column["name"] for column in sa.inspect(bind).get_columns("notes")}:
        op.add_column(
            "notes",
            sa.Column("tags", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        )
        op.alter_column("notes", "tags", server_default=None)
    bookmark_columns = {
        column["name"]: column["type"] for column in sa.inspect(bind).get_columns("bookmarks")
    }
    if bind.dialect.name == "postgresql" and isinstance(
        bookmark_columns.get("target_id"), postgresql.UUID
    ):
        # Bookmark targets may be UUIDs or stable CMS/festival slugs. Preserve
        # existing UUID values as text while allowing both forms going forward.
        op.alter_column(
            "bookmarks",
            "target_id",
            existing_type=sa.UUID(),
            type_=sa.String(length=128),
            postgresql_using="target_id::text",
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.alter_column(
            "bookmarks",
            "target_id",
            existing_type=sa.String(length=128),
            type_=sa.UUID(),
            postgresql_using="NULLIF(target_id, '')::uuid",
        )
    if "tags" in {column["name"] for column in sa.inspect(bind).get_columns("notes")}:
        op.drop_column("notes", "tags")
