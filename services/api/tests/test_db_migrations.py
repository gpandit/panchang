"""Offline-service migration smoke test.

The test deliberately supplies an isolated SQLite connection to Alembic.  It
does not replace the PostgreSQL/PostGIS deployment path; it proves a fresh
checkout can execute the migration chain without a hidden local service.  The
same connection injection seam is available to a CI job that supplies a real
PostgreSQL connection.
"""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from alembic import command
from api.db import Base
from api.db import models as _models  # noqa: F401

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
                connection.execute(text("SELECT COUNT(*) FROM temple_admin_accounts")).scalar_one()
                == 1
            )
    finally:
        engine.dispose()


def test_foundation_migration_does_not_backdate_later_tables() -> None:
    # Load through Alembic's script directory rather than importing a numeric
    # module name as an ordinary Python package.
    config = _alembic_config()
    revision = ScriptDirectory.from_config(config).get_revision("0002_v3_data_model")
    assert revision is not None
    foundation = revision.module
    assert len(foundation._V3_TABLES) == 56
    assert foundation._V3_TABLES <= set(Base.metadata.tables)
    assert {"idempotency_keys", "outbox_events"}.isdisjoint(foundation._V3_TABLES)
