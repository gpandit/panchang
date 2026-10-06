"""Transactional outbox and command replay guards.

This revision is additive.  Revision 0002 builds tables from declarative
metadata, so a fresh checkout may already have these two tables when 0002 runs
with a newer model module.  ``create_all(checkfirst=True)`` deliberately makes
this revision safe for both that path and an existing database upgraded from
0002 before the model was added.

Revision ID: 0003_s005_outbox_idempotency
Revises: 0002_v3_data_model
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from api.db import Base
from api.db import models as _models  # noqa: F401  # register metadata tables

revision: str = "0003_s005_outbox_idempotency"
down_revision: str | None = "0002_v3_data_model"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(
        bind=bind,
        tables=[
            Base.metadata.tables["idempotency_keys"],
            Base.metadata.tables["outbox_events"],
        ],
        checkfirst=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    # Outbox references idempotency keys, therefore drop it first.
    Base.metadata.tables["outbox_events"].drop(bind=bind, checkfirst=True)
    Base.metadata.tables["idempotency_keys"].drop(bind=bind, checkfirst=True)
