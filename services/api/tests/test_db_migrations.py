"""Offline-service migration smoke test.

The test deliberately supplies an isolated SQLite connection to Alembic.  It
does not replace the PostgreSQL/PostGIS deployment path; it proves a fresh
checkout can execute the migration chain without a hidden local service.  The
same connection injection seam is available to a CI job that supplies a real
PostgreSQL connection.
"""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


API_ROOT = Path(__file__).parents[1]


def _alembic_config() -> Config:
    config = Config(str(API_ROOT / "alembic.ini"))
    # alembic.ini intentionally uses a path relative to the API working
    # directory.  Tests run from the repository root, so make it explicit.
    config.set_main_option("script_location", str(API_ROOT / "alembic"))
    return config


def test_alembic_upgrade_head_on_isolated_database(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'migration-smoke.db'}")
    try:
        with engine.connect() as connection:
            config = _alembic_config()
            config.attributes["connection"] = connection
            command.upgrade(config, "head")

        tables = set(inspect(engine).get_table_names())
        assert {
            "alembic_version",
            "temples",
            "temple_admin_accounts",
            "users",
            "panchang_days",
            "reminders",
            "provider_accounts",
            "ledger_journals",
            "bookings",
            "order_refs",
            "idempotency_keys",
            "outbox_events",
        } <= tables
        with engine.connect() as connection:
            assert connection.execute(text("SELECT COUNT(*) FROM temples")).scalar_one() == 1
            assert (
                connection.execute(
                    text("SELECT COUNT(*) FROM temple_admin_accounts")
                ).scalar_one()
                == 1
            )
    finally:
        engine.dispose()
