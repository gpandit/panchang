"""service taxonomy seed (F5)

Seeds the admin-curated ``ServiceType`` catalogue (Architecture v1.2 §3 / dev-plan
F5): festival-officiation types that reuse the **real** festival ids already served
by the CMS content store (``api.cms.store``, §5.5 in the requirement spec), pujas/
ceremonies whose ``muhurat_event_ref`` names the **real** muhurat period labels the
Panchang engine computes (``panchang.compute._compute_muhurat``, §5.6.1), plus
optional astrology/consultation service types with no festival/muhurat link.

**Real identifiers referenced (not invented):**

- Festival ids — grepped from ``services/api/src/api/cms/store.py`` (``_SEED``):
  ``fest-diwali``, ``fest-holi``, ``fest-navratri``. (``fest-ekadashi-draft`` is
  excluded — its ``status`` is ``"draft"``, i.e. not real/published content.)
- Muhurat event names — grepped from
  ``services/panchang/src/panchang/compute.py`` (``_compute_muhurat``), the exact
  ``MuhuratPeriod.name`` strings the engine emits: ``"Rahu Kalam"``,
  ``"Yamaganda"``, ``"Gulika Kalam"``, ``"Abhijit Muhurat"``, ``"Brahma Muhurat"``,
  ``"Nishita Muhurat"``. There is no separate slug/id table for these in the
  codebase (``api.panchang_view._muhurat_type`` itself matches on these literal
  name strings), so the name *is* the real identifier and is stored verbatim in
  ``muhurat_event_ref``.

**Idempotency.** Every row is keyed on its stable ``id``. ``upgrade()`` does a
portable "insert, or update if already present" per row (checked via a plain
``SELECT`` first) so re-running ``alembic upgrade head`` — or a future re-seed —
never fails on a duplicate primary key and always converges rows to the seed
values. This works identically on SQLite (aiosqlite tests) and Postgres; no
dialect-specific ``ON CONFLICT``/``MERGE`` is used.

Revision ID: 0004_service_taxonomy_seed
Revises: 0003_vault_tables
Create Date: 2026-07-07
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_service_taxonomy_seed"
down_revision: str | None = "0003_vault_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# JSONB on Postgres, JSON elsewhere (matches api.db.base.JSON_VARIANT).
JSON_VARIANT = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

# ── Real festival ids (services/api/src/api/cms/store.py::_SEED, published only) ──
FEST_DIWALI = "fest-diwali"
FEST_HOLI = "fest-holi"
FEST_NAVRATRI = "fest-navratri"

# ── Real muhurat event names (services/panchang/src/panchang/compute.py::_compute_muhurat) ──
MUHURAT_ABHIJIT = "Abhijit Muhurat"
MUHURAT_BRAHMA = "Brahma Muhurat"
MUHURAT_NISHITA = "Nishita Muhurat"
MUHURAT_RAHU_KALAM = "Rahu Kalam"

SERVICE_TYPES: list[dict[str, Any]] = [
    # ── Festival officiation (festival_ref → real published CMS festival ids) ──
    {
        "id": "svctype-diwali-lakshmi-puja",
        "category": "festival_officiation",
        "name": "Diwali Lakshmi Puja",
        "festival_ref": FEST_DIWALI,
        "muhurat_event_ref": None,
        "taxonomy_tags": ["festival", "diwali", "lakshmi", "officiation"],
    },
    {
        "id": "svctype-holika-dahan",
        "category": "festival_officiation",
        "name": "Holika Dahan Officiation",
        "festival_ref": FEST_HOLI,
        "muhurat_event_ref": MUHURAT_RAHU_KALAM,
        "taxonomy_tags": ["festival", "holi", "holika-dahan", "officiation"],
    },
    {
        "id": "svctype-navratri-durga-puja",
        "category": "festival_officiation",
        "name": "Navratri Durga Puja",
        "festival_ref": FEST_NAVRATRI,
        "muhurat_event_ref": None,
        "taxonomy_tags": ["festival", "navratri", "durga", "officiation"],
    },
    # ── Pujas / ceremonies (muhurat_event_ref → real muhurat period names) ─────
    {
        "id": "svctype-griha-pravesh",
        "category": "puja",
        "name": "Griha Pravesh (Housewarming)",
        "festival_ref": None,
        "muhurat_event_ref": MUHURAT_ABHIJIT,
        "taxonomy_tags": ["puja", "griha-pravesh", "housewarming", "muhurat-aware"],
    },
    {
        "id": "svctype-satyanarayan-puja",
        "category": "puja",
        "name": "Satyanarayan Puja",
        "festival_ref": None,
        "muhurat_event_ref": MUHURAT_ABHIJIT,
        "taxonomy_tags": ["puja", "satyanarayan", "muhurat-aware"],
    },
    {
        "id": "svctype-havan-yagna",
        "category": "puja",
        "name": "Havan / Yagna",
        "festival_ref": None,
        "muhurat_event_ref": MUHURAT_BRAHMA,
        "taxonomy_tags": ["puja", "havan", "yagna", "muhurat-aware"],
    },
    {
        "id": "svctype-shanti-path",
        "category": "puja",
        "name": "Shanti Path (Peace Ceremony)",
        "festival_ref": None,
        "muhurat_event_ref": MUHURAT_NISHITA,
        "taxonomy_tags": ["puja", "shanti-path", "muhurat-aware"],
    },
    {
        "id": "svctype-vivah-sanskar",
        "category": "ceremony",
        "name": "Vivah Sanskar (Wedding)",
        "festival_ref": None,
        "muhurat_event_ref": MUHURAT_ABHIJIT,
        "taxonomy_tags": ["ceremony", "vivah", "wedding", "muhurat-aware"],
    },
    {
        "id": "svctype-mundan-sanskar",
        "category": "ceremony",
        "name": "Mundan Sanskar (First Haircut)",
        "festival_ref": None,
        "muhurat_event_ref": None,
        "taxonomy_tags": ["ceremony", "mundan", "sanskar"],
    },
    {
        "id": "svctype-namkaran-sanskar",
        "category": "ceremony",
        "name": "Namkaran Sanskar (Naming Ceremony)",
        "festival_ref": None,
        "muhurat_event_ref": None,
        "taxonomy_tags": ["ceremony", "namkaran", "sanskar"],
    },
    {
        "id": "svctype-antyeshti",
        "category": "ceremony",
        "name": "Antyeshti (Funeral Rites)",
        "festival_ref": None,
        "muhurat_event_ref": None,
        "taxonomy_tags": ["ceremony", "antyeshti", "funeral-rites"],
    },
    # ── Astrology / consultation (optional category — no festival/muhurat link) ──
    {
        "id": "svctype-janam-kundali",
        "category": "astrology_consultation",
        "name": "Janam Kundali Reading",
        "festival_ref": None,
        "muhurat_event_ref": None,
        "taxonomy_tags": ["astrology", "kundali", "consultation"],
    },
    {
        "id": "svctype-muhurat-consultation",
        "category": "astrology_consultation",
        "name": "Muhurat Selection Consultation",
        "festival_ref": None,
        "muhurat_event_ref": MUHURAT_ABHIJIT,
        "taxonomy_tags": ["astrology", "muhurat", "consultation"],
    },
    {
        "id": "svctype-vastu-consultation",
        "category": "astrology_consultation",
        "name": "Vastu Shastra Consultation",
        "festival_ref": None,
        "muhurat_event_ref": None,
        "taxonomy_tags": ["astrology", "vastu", "consultation"],
    },
]


def _service_types_table() -> sa.Table:
    metadata = sa.MetaData()
    return sa.Table(
        "service_types",
        metadata,
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("category", sa.String()),
        sa.Column("name", sa.String()),
        sa.Column("festival_ref", sa.String()),
        sa.Column("muhurat_event_ref", sa.String()),
        sa.Column("taxonomy_tags", JSON_VARIANT),
    )


def upgrade() -> None:
    """Insert-or-update each ServiceType by id — dialect-neutral, safe to re-run."""
    bind = op.get_bind()
    table = _service_types_table()

    existing_ids = {
        row[0]
        for row in bind.execute(sa.select(table.c.id)).fetchall()
        if row[0] in {row_data["id"] for row_data in SERVICE_TYPES}
    }

    to_insert = [row for row in SERVICE_TYPES if row["id"] not in existing_ids]
    to_update = [row for row in SERVICE_TYPES if row["id"] in existing_ids]

    if to_insert:
        bind.execute(sa.insert(table), to_insert)

    for row in to_update:
        bind.execute(
            sa.update(table)
            .where(table.c.id == row["id"])
            .values(**{k: v for k, v in row.items() if k != "id"})
        )


def downgrade() -> None:
    """Remove exactly the rows this migration seeded, by id."""
    bind = op.get_bind()
    table = _service_types_table()
    seeded_ids = [row["id"] for row in SERVICE_TYPES]
    bind.execute(sa.delete(table).where(table.c.id.in_(seeded_ids)))
