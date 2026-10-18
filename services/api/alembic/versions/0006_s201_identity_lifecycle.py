"""Identity lifecycle state and durable export/deletion request records.

Revision ID: 0006_s201_identity_lifecycle
Revises: 0005_user_data_rls
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op
from api.db import Base
from api.db import models as _models  # noqa: F401  # register metadata tables

revision: str = "0006_s201_identity_lifecycle"
down_revision: str | None = "0005_user_data_rls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("users")}
    additions = (
        ("status", sa.String(length=16), "active"),
        ("deletion_requested_at", sa.DateTime(timezone=True), None),
        ("deleted_at", sa.DateTime(timezone=True), None),
    )
    for name, column_type, default in additions:
        if name not in columns:
            op.add_column(
                "users",
                sa.Column(name, column_type, nullable=name == "status", server_default=default),
            )

    user_jobs = Base.metadata.tables["user_jobs"]
    user_jobs.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.tables["user_jobs"].drop(bind=bind, checkfirst=True)
    columns = {column["name"] for column in inspect(bind).get_columns("users")}
    for name in ("deleted_at", "deletion_requested_at", "status"):
        if name in columns:
            op.drop_column("users", name)
