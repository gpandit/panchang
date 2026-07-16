"""provider onboarding state + agreement acceptances (A1)

Adds the provider-onboarding half of the marketplace schema (dev-plan
``docs/dev-plan-marketplace.md`` step A1):

* ``pandits.onboarding_state`` — the DRAFT/SUBMITTED/APPROVED/REJECTED/
  CHANGES_REQUESTED state machine column (defaults to ``draft`` for both new and
  already-existing rows via ``server_default``, so this is a safe additive change).
* ``agreement_acceptances`` — one row per (pandit, agreement_type, version)
  acceptance event: versioned + logged (who + when), append-only.

Dialect-neutral: plain ``String``/``DateTime(timezone=True)`` columns and a
``server_default`` for the new NOT NULL column, so this applies cleanly on both
aiosqlite (tests) and Postgres — no Postgres-only constructs here (contrast with
0002's ExcludeConstraint).

Revision ID: 0005_provider_onboarding
Revises: 0004_service_taxonomy_seed
Create Date: 2026-07-07
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_provider_onboarding"
down_revision: str | None = "0004_service_taxonomy_seed"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pandits",
        sa.Column(
            "onboarding_state",
            sa.String(),
            nullable=False,
            server_default="draft",
        ),
    )
    op.create_index("ix_pandits_onboarding_state", "pandits", ["onboarding_state"])

    op.create_table(
        "agreement_acceptances",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "pandit_id",
            sa.String(),
            sa.ForeignKey("pandits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("agreement_type", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("accepted_by", sa.String(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agreement_acceptances_pandit_id", "agreement_acceptances", ["pandit_id"])
    op.create_index(
        "ix_agreement_acceptances_agreement_type", "agreement_acceptances", ["agreement_type"]
    )
    op.create_index(
        "ix_agreement_acceptances_pandit_type",
        "agreement_acceptances",
        ["pandit_id", "agreement_type"],
    )


def downgrade() -> None:
    op.drop_table("agreement_acceptances")
    op.drop_index("ix_pandits_onboarding_state", table_name="pandits")
    op.drop_column("pandits", "onboarding_state")
