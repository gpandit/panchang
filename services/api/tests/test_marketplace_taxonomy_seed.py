"""Tests for the F5 service taxonomy seed migration.

Proves the acceptance criterion from ``docs/dev-plan-marketplace.md`` step F5:
seeded ``ServiceType`` rows are queryable after ``alembic upgrade head`` and each
one carries the optional ``festival_ref`` / ``muhurat_event_ref`` link exactly as
the seed data intends — and that those links are **real** ids, not invented ones
(a real, published CMS festival id; a real muhurat period name the Panchang
engine emits).

The migration chain (0001 → 0004) is applied **online** against a fresh, isolated
temp-file SQLite database — not the shared in-memory test DB other suites use —
so this test doesn't disturb (or depend on) other tests' schema state. 0001's demo
seed calls ``api.auth.hash_password`` at import time, which only works when
migrations run online (not ``--sql`` offline rendering), so this exercises the
same "online apply" path required by the F5 done-when.
"""

from __future__ import annotations

import importlib.util
import os
import pathlib
import tempfile
from collections.abc import Iterator
from types import ModuleType

import pytest
import sqlalchemy as sa
from alembic.config import Config
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext

from alembic import command


def _alembic_ini_path() -> str:
    return str(pathlib.Path(__file__).resolve().parents[1] / "alembic.ini")


def _versions_dir() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[1] / "alembic" / "versions"


def _load_seed_migration_module() -> ModuleType:
    """Import the 0004 migration file directly (its filename isn't a valid module path)."""
    path = _versions_dir() / "0004_service_taxonomy_seed.py"
    spec = importlib.util.spec_from_file_location("_f5_seed_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SEED_MODULE = _load_seed_migration_module()
SERVICE_TYPES = SEED_MODULE.SERVICE_TYPES


@pytest.fixture
def migrated_sqlite_engine() -> Iterator[sa.Engine]:
    """Apply the full migration chain (0001→0004) to a fresh temp sqlite file.

    ``alembic/env.py`` runs migrations through ``api.db.get_engine()``, which in
    turn reads ``api.settings.get_settings().database_url``. Both are memoised
    process-wide singletons: ``get_settings()`` caches the *first* ``Settings()``
    it ever builds (picking up the shared in-memory DB URL set by
    ``tests/conftest.py``), and ``get_engine()`` caches an engine built from that
    URL. Pointing ``API_DATABASE_URL`` at our temp file DB has no effect unless
    both caches are cleared, so we reset the settings singleton *and* call
    ``reset_engine()`` before invoking Alembic, then restore both afterwards so
    other tests are unaffected.
    """
    import api.settings as settings_module
    from api.db.session import reset_engine

    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = pathlib.Path(tmp_dir) / "f5_taxonomy_seed.sqlite3"
        db_url = f"sqlite:///{db_path}"

        previous = os.environ.get("API_DATABASE_URL")
        previous_settings = settings_module._settings
        os.environ["API_DATABASE_URL"] = db_url
        settings_module._settings = None
        reset_engine()
        try:
            cfg = Config(_alembic_ini_path())
            # ``script_location = alembic`` in alembic.ini is relative to the CWD
            # alembic is invoked from (normally ``services/api``); pin it to an
            # absolute path so this test is CWD-independent under pytest.
            cfg.set_main_option(
                "script_location", str(pathlib.Path(__file__).resolve().parents[1] / "alembic")
            )
            command.upgrade(cfg, "head")

            engine = sa.create_engine(db_url, future=True)
            try:
                yield engine
            finally:
                engine.dispose()
        finally:
            if previous is None:
                os.environ.pop("API_DATABASE_URL", None)
            else:
                os.environ["API_DATABASE_URL"] = previous
            settings_module._settings = previous_settings
            reset_engine()


def _fetch_service_types(engine: sa.Engine) -> dict[str, dict[str, object]]:
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("SELECT id, category, name, festival_ref, muhurat_event_ref FROM service_types")
        ).fetchall()
    return {
        row[0]: {
            "category": row[1],
            "name": row[2],
            "festival_ref": row[3],
            "muhurat_event_ref": row[4],
        }
        for row in rows
    }


def test_seeded_service_types_are_queryable_after_migration(
    migrated_sqlite_engine: sa.Engine,
) -> None:
    found = _fetch_service_types(migrated_sqlite_engine)
    seeded_ids = {row["id"] for row in SERVICE_TYPES}
    assert seeded_ids <= set(found), "every seeded ServiceType id must be present after migration"
    assert len(SERVICE_TYPES) >= 10  # festival + puja/ceremony + astrology coverage


def test_each_seeded_row_matches_its_fixture_links(migrated_sqlite_engine: sa.Engine) -> None:
    """Persisted festival_ref/muhurat_event_ref match exactly what the fixture defines."""
    found = _fetch_service_types(migrated_sqlite_engine)
    for seed in SERVICE_TYPES:
        persisted = found[seed["id"]]
        assert persisted["festival_ref"] == seed["festival_ref"]
        assert persisted["muhurat_event_ref"] == seed["muhurat_event_ref"]


def test_at_least_one_seeded_service_type_links_a_real_festival_id(
    migrated_sqlite_engine: sa.Engine,
) -> None:
    """festivalRef values must be real CMS festival ids, not invented ones."""
    from api.cms.store import list_festivals

    real_festival_ids = {f.id for f in list_festivals(published_only=True)}
    linked = {row["festival_ref"] for row in SERVICE_TYPES if row["festival_ref"]}

    assert linked, "expected at least one ServiceType to carry a festivalRef"
    assert linked <= real_festival_ids


def test_at_least_one_seeded_service_type_links_a_real_muhurat_event(
    migrated_sqlite_engine: sa.Engine,
) -> None:
    """muhuratEventRef values must be real muhurat period names the engine emits.

    Mirrors the literal ``MuhuratPeriod.name`` strings produced by
    ``panchang.compute._compute_muhurat`` (Rahu Kalam / Yamaganda / Gulika Kalam /
    Abhijit Muhurat / Brahma Muhurat / Nishita Muhurat) — there is no separate
    slug/id table for these in the codebase, so the name is the real identifier.
    """
    real_muhurat_names = {
        "Rahu Kalam",
        "Yamaganda",
        "Gulika Kalam",
        "Abhijit Muhurat",
        "Brahma Muhurat",
        "Nishita Muhurat",
    }
    linked = {row["muhurat_event_ref"] for row in SERVICE_TYPES if row["muhurat_event_ref"]}

    assert linked, "expected at least one ServiceType to carry a muhuratEventRef"
    assert linked <= real_muhurat_names


def test_seed_upgrade_is_idempotent_on_rerun(migrated_sqlite_engine: sa.Engine) -> None:
    """Re-running the seed's upgrade() against the same DB must not duplicate/fail."""
    with migrated_sqlite_engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        op = Operations(ctx)
        # A second application of the same upgrade() must not raise (no PK
        # collision) and must leave row values unchanged (upsert, not insert).
        SEED_MODULE.op = op  # migration module calls op.get_bind() internally
        SEED_MODULE.upgrade()
        conn.commit()

    found = _fetch_service_types(migrated_sqlite_engine)
    assert len(found) == len({row["id"] for row in SERVICE_TYPES}.union(found))
    for seed in SERVICE_TYPES:
        persisted = found[seed["id"]]
        assert persisted["festival_ref"] == seed["festival_ref"]
        assert persisted["muhurat_event_ref"] == seed["muhurat_event_ref"]
