"""initial temple schema + demo seed

Creates the ``temples`` and ``temple_admin_accounts`` tables and seeds one demo
temple + admin login, so the Temple Display and admin console are usable as soon as
``alembic upgrade head`` finishes. The seed is keyed on a stable id and mirrors
``api.temple.store.seed()``, which is idempotent against it.

Revision ID: 0001_initial_temple
Revises:
Create Date: 2026-06-15
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial_temple"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# JSONB on Postgres, JSON elsewhere (matches api.db.base.JSON_VARIANT).
JSON_VARIANT = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

DEMO_TEMPLE_ID = "temple-siddhivinayak"
DEMO_ADMIN_EMAIL = "admin@siddhivinayak.temple"
DEMO_ADMIN_PASSWORD = "templeadmin"  # demo seed credential only


def upgrade() -> None:
    op.create_table(
        "temples",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("name_dev", sa.String(), nullable=False),
        sa.Column("tagline", sa.String(), nullable=False, server_default=""),
        sa.Column("location", JSON_VARIANT, nullable=False),
        sa.Column("aarti", JSON_VARIANT, nullable=False),
        sa.Column("events", JSON_VARIANT, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.String(), nullable=True),
    )
    op.create_table(
        "temple_admin_accounts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("salt", sa.String(), nullable=False),
        sa.Column(
            "temple_id",
            sa.String(),
            sa.ForeignKey("temples.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_temple_admin_accounts_email",
        "temple_admin_accounts",
        ["email"],
        unique=True,
    )

    _seed_demo()


def downgrade() -> None:
    op.drop_index("ix_temple_admin_accounts_email", table_name="temple_admin_accounts")
    op.drop_table("temple_admin_accounts")
    op.drop_table("temples")


def _seed_demo() -> None:
    # Imported here so the module loads even if app code is unavailable at autogen time.
    from api.auth import hash_password

    now = datetime.now(UTC)
    temples = sa.table(
        "temples",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("name_dev", sa.String),
        sa.column("tagline", sa.String),
        sa.column("location", JSON_VARIANT),
        sa.column("aarti", JSON_VARIANT),
        sa.column("events", JSON_VARIANT),
        sa.column("updated_at", sa.DateTime(timezone=True)),
        sa.column("updated_by", sa.String),
    )
    accounts = sa.table(
        "temple_admin_accounts",
        sa.column("id", sa.String),
        sa.column("email", sa.String),
        sa.column("password_hash", sa.String),
        sa.column("salt", sa.String),
        sa.column("temple_id", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )

    op.bulk_insert(
        temples,
        [
            {
                "id": DEMO_TEMPLE_ID,
                "name": "Shree Siddhivinayak Mandir",
                "name_dev": "श्री सिद्धिविनायक मंदिर",
                "tagline": "Sanātana Dharma",
                "location": {
                    "label": "Dubai · United Arab Emirates",
                    "lat": 25.2048,
                    "lon": 55.2708,
                    "tz": "Asia/Dubai",
                },
                "aarti": [
                    {
                        "key": "mangala",
                        "name": "Maṅgala Ārati",
                        "dev": "मंगला आरती",
                        "time": "05:00",
                        "note": "Awakening",
                        "nat": {},
                    },
                    {
                        "key": "shringar",
                        "name": "Śṛṅgāra Ārati",
                        "dev": "शृंगार आरती",
                        "time": "08:30",
                        "note": "Adornment",
                        "nat": {},
                    },
                    {
                        "key": "rajbhog",
                        "name": "Rājbhoga Ārati",
                        "dev": "राजभोग आरती",
                        "time": "12:00",
                        "note": "Midday bhoga",
                        "nat": {},
                    },
                    {
                        "key": "sandhya",
                        "name": "Sandhyā Ārati",
                        "dev": "संध्या आरती",
                        "time": "19:00",
                        "note": "Dusk",
                        "nat": {},
                    },
                    {
                        "key": "shayan",
                        "name": "Śayana Ārati",
                        "dev": "शयन आरती",
                        "time": "20:45",
                        "note": "Rest",
                        "nat": {},
                    },
                ],
                "events": [
                    {
                        "id": "evt-sankashti",
                        "title": "Sankashti Chaturthi",
                        "title_dev": "संकष्टी चतुर्थी",
                        "date": "2026-06-08",
                        "time": None,
                        "description": "Special Ganesha abhishekam after Sandhyā Ārati.",
                    }
                ],
                "updated_at": now,
                "updated_by": "system",
            }
        ],
    )

    password_hash, salt = hash_password(DEMO_ADMIN_PASSWORD)
    op.bulk_insert(
        accounts,
        [
            {
                "id": "tadmin-demo0001",
                "email": DEMO_ADMIN_EMAIL,
                "password_hash": password_hash,
                "salt": salt,
                "temple_id": DEMO_TEMPLE_ID,
                "created_at": now,
            }
        ],
    )
