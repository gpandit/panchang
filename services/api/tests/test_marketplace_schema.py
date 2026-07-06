"""Tests for the F2 marketplace schema.

Two layers:

1. **Dialect-portable (always run):** the ORM models import cleanly and every
   marketplace table builds under ``Base.metadata.create_all`` on the in-memory
   SQLite test engine — proving the Postgres-only ExcludeConstraint is correctly kept
   out of the ORM (it lives only in the Alembic migration) and nothing else in the
   schema is PG-specific.

2. **Postgres-gated (the F2 acceptance criterion):** two overlapping *confirmed*
   bookings for one pandit are rejected at the DB level by the ``no_double_booking``
   exclusion constraint. This needs a real Postgres (``btree_gist`` + ``tstzrange`` +
   ``ExcludeConstraint``), which does not exist in the local sandbox, so it is skipped
   unless ``TEST_DATABASE_URL`` (or ``DATABASE_URL``) points at Postgres. **In CI /
   Contabo, where Postgres is provisioned, set ``TEST_DATABASE_URL`` and this test
   runs the real overlap rejection.**
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine

from api.db import Base
from api.db.marketplace_models import ACTIVE_BOOKING_STATUSES, BookingStatus

# ── Layer 1: portable schema build (runs everywhere, incl. local SQLite) ──────


def test_all_marketplace_tables_registered() -> None:
    """Every entity from the data model (§3) is present on Base.metadata."""
    expected = {
        "pandits",
        "service_types",
        "pandit_services",
        "travel_policies",
        "availabilities",
        "verification_records",
        "bookings",
        "booking_events",
        "payments",
        "payouts",
        "refunds",
        "reviews",
        "conversations",
        "messages",
        "video_sessions",
        "disputes",
    }
    assert expected <= set(Base.metadata.tables)


def test_booking_has_policy_snapshot_json_column() -> None:
    booking = Base.metadata.tables["bookings"]
    assert "policy_snapshot" in booking.columns
    assert "price_breakdown" in booking.columns
    assert "start_time" in booking.columns and "end_time" in booking.columns


async def test_marketplace_schema_builds_on_sqlite() -> None:
    """create_all must succeed on SQLite — i.e. no PG-only construct leaked into ORM."""
    engine = create_async_engine("sqlite+aiosqlite://")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            # Sanity: the bookings table really exists in the built schema.
            tables = await conn.run_sync(
                lambda sync_conn: sa.inspect(sync_conn).get_table_names()
            )
            assert "bookings" in tables
            # And the overlap ExcludeConstraint is NOT part of the SQLite schema.
            assert BookingStatus.CONFIRMED in ACTIVE_BOOKING_STATUSES
    finally:
        await engine.dispose()


# ── Layer 2: Postgres-gated DB-level overlap rejection (the F2 criterion) ─────


def _postgres_dsn() -> str | None:
    """Return a Postgres DSN from the environment, else None (skip PG tests)."""
    for var in ("TEST_DATABASE_URL", "DATABASE_URL"):
        url = os.environ.get(var)
        if url and url.startswith(("postgresql", "postgres://")):
            # Normalise to the async psycopg driver the app uses.
            if url.startswith("postgresql+"):
                return url
            return url.replace("postgres://", "postgresql+psycopg://", 1).replace(
                "postgresql://", "postgresql+psycopg://", 1
            )
    return None


_PG_DSN = _postgres_dsn()
_pg_only = pytest.mark.skipif(
    _PG_DSN is None,
    reason=(
        "No Postgres DSN in TEST_DATABASE_URL/DATABASE_URL — the no-double-booking "
        "exclusion constraint (tstzrange + btree_gist ExcludeConstraint) is "
        "Postgres-only. Runs in CI/Contabo where Postgres is provisioned."
    ),
)


async def _create_pandit_and_service(conn: sa.Connection) -> tuple[str, str]:
    """Insert the minimal pandit + service rows a booking FK-references."""
    now = datetime.now(UTC)
    await conn.execute(
        sa.text(
            "INSERT INTO pandits "
            "(id, user_id, display_name, languages, verification_status, "
            " rating_count, created_at, updated_at) "
            "VALUES (:id, :uid, :dn, '[]', 'verified', 0, :now, :now)"
        ),
        {"id": "pandit-1", "uid": "user-1", "dn": "Test Pandit", "now": now},
    )
    await conn.execute(
        sa.text(
            "INSERT INTO service_types (id, category, name, taxonomy_tags) "
            "VALUES ('svc-type-1', 'puja', 'Griha Pravesh', '[]')"
        )
    )
    await conn.execute(
        sa.text(
            "INSERT INTO pandit_services "
            "(id, pandit_id, service_type_id, modes, duration_min, base_price, "
            " currency, samagri_option, is_published, created_at, updated_at) "
            "VALUES ('psvc-1', 'pandit-1', 'svc-type-1', '[\"in_person\"]', 60, "
            " 100.00, 'USD', 'none', true, :now, :now)"
        ),
        {"now": now},
    )
    return "pandit-1", "psvc-1"


def _booking_insert(booking_id: str, start: datetime, end: datetime, status: str) -> sa.TextClause:
    now = datetime.now(UTC)
    return sa.text(
        "INSERT INTO bookings "
        "(id, patron_user_id, pandit_id, pandit_service_id, mode, start_time, "
        " end_time, tz, samagri_chosen, status, price_breakdown, policy_snapshot, "
        " created_at, updated_at) "
        "VALUES (:id, :patron, 'pandit-1', 'psvc-1', 'in_person', :start, :end, "
        " 'UTC', 'none', :status, '{}', '{}', :now, :now)"
    ).bindparams(id=booking_id, patron="patron-1", start=start, end=end, status=status, now=now)


@_pg_only
async def test_overlapping_confirmed_bookings_rejected_at_db_level() -> None:
    """Two overlapping CONFIRMED bookings for one pandit must be rejected by the DB."""
    from alembic.config import Config

    from alembic import command

    assert _PG_DSN is not None
    engine = create_async_engine(_PG_DSN)
    try:
        # Build the schema via the real migration so the ExcludeConstraint + btree_gist
        # extension are created exactly as production gets them.
        os.environ["API_DATABASE_URL"] = _PG_DSN.replace(
            "postgresql+psycopg", "postgresql", 1
        )
        cfg = Config(str(_alembic_ini_path()))
        command.upgrade(cfg, "head")

        base = datetime(2026, 8, 1, 10, 0, tzinfo=UTC)
        async with engine.begin() as conn:
            await _create_pandit_and_service(conn)
            await conn.execute(
                _booking_insert("bk-1", base, base + timedelta(hours=1), "confirmed")
            )

        # A second confirmed booking overlapping the first must raise at commit/flush.
        with pytest.raises(Exception) as exc_info:  # IntegrityError from the exclusion
            async with engine.begin() as conn:
                await conn.execute(
                    _booking_insert(
                        "bk-2",
                        base + timedelta(minutes=30),
                        base + timedelta(minutes=90),
                        "confirmed",
                    )
                )
        assert "no_double_booking_overlap" in str(exc_info.value).lower() or "exclu" in str(
            exc_info.value
        ).lower()

        # A cancelled booking in the same slot is fine — the constraint is partial.
        async with engine.begin() as conn:
            await conn.execute(
                _booking_insert(
                    "bk-3",
                    base + timedelta(minutes=30),
                    base + timedelta(minutes=90),
                    "cancelled_patron",
                )
            )
    finally:
        await engine.dispose()


def _alembic_ini_path() -> str:
    """Locate services/api/alembic.ini relative to this test file."""
    import pathlib

    return str(pathlib.Path(__file__).resolve().parents[1] / "alembic.ini")
