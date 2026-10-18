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
    columns = {column["name"]: column for column in inspect(bind).get_columns("users")}
    if "status" not in columns:
        op.add_column(
            "users",
            sa.Column("status", sa.String(length=16), nullable=True, server_default="active"),
        )
    op.execute(sa.text("UPDATE users SET status = 'active' WHERE status IS NULL"))
    for name in ("deletion_requested_at", "deleted_at"):
        if name not in columns:
            op.add_column("users", sa.Column(name, sa.DateTime(timezone=True), nullable=True))

    constraints = {
        constraint["name"] for constraint in inspect(bind).get_check_constraints("users")
    }
    status_needs_alter = (
        not constraints.__contains__("ck_users_status")
        or columns.get("status", {"nullable": True})["nullable"]
    )
    if status_needs_alter and bind.dialect.name == "sqlite":
        with op.batch_alter_table("users", recreate="always") as batch:
            batch.alter_column(
                "status",
                existing_type=sa.String(length=16),
                nullable=False,
                existing_server_default=sa.text("'active'"),
            )
            if "ck_users_status" not in constraints:
                batch.create_check_constraint(
                    "ck_users_status", "status IN ('active','deleting','deleted')"
                )
    else:
        if columns.get("status", {"nullable": True})["nullable"]:
            op.alter_column(
                "users",
                "status",
                existing_type=sa.String(length=16),
                nullable=False,
                existing_server_default=sa.text("'active'"),
            )
        if "ck_users_status" not in constraints:
            op.create_check_constraint(
                "ck_users_status", "users", "status IN ('active','deleting','deleted')"
            )

    user_jobs = Base.metadata.tables["user_jobs"]
    user_jobs.create(bind=bind, checkfirst=True)
    if bind.dialect.name == "postgresql":
        index_names = {index["name"] for index in inspect(bind).get_indexes("user_jobs")}
        if "uq_user_jobs_open" not in index_names:
            op.create_index(
                "uq_user_jobs_open",
                "user_jobs",
                ["user_id", "kind"],
                unique=True,
                postgresql_where=sa.text("status IN ('queued', 'processing')"),
            )
        op.execute('ALTER TABLE "user_jobs" ENABLE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "user_jobs" FORCE ROW LEVEL SECURITY')
        op.execute('DROP POLICY IF EXISTS "rls_user_jobs_owner" ON "user_jobs"')
        op.execute(
            """CREATE POLICY "rls_user_jobs_owner" ON "user_jobs"
               USING (current_setting('app.user_id', true) = "user_id"::text)
               WITH CHECK (current_setting('app.user_id', true) = "user_id"::text)"""
        )


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.tables["user_jobs"].drop(bind=bind, checkfirst=True)
    columns = {column["name"] for column in inspect(bind).get_columns("users")}
    for name in ("deleted_at", "deletion_requested_at", "status"):
        if name in columns:
            op.drop_column("users", name)
