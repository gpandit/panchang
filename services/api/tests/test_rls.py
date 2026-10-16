"""PostgreSQL RLS evidence for user-owned tables.

This module is deliberately opt-in.  It requires
``PANCHANG_TEST_RLS_URL`` to point at a disposable PostgreSQL database whose
name ends in ``_test``; normal SQLite/unit tests never need credentials or a
running service.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from alembic import command
from api.db.session import _sync_url

API_ROOT = Path(__file__).parents[1]
EXPECTED_POLICIES = {
    "user_preferences",
    "locations",
    "family_groups",
    "family_memberships",
    "vault_refs",
    "devices",
    "legal_acceptances",
    "notes",
    "bookmarks",
    "reminders",
    "vrat_records",
    "planner_requests",
    "calendar_jobs",
    "subscriptions",
    "provider_accounts",
}


@pytest.fixture(scope="module")
def rls_url() -> str:
    url = os.environ.get("PANCHANG_TEST_RLS_URL")
    if not url:
        pytest.skip("set PANCHANG_TEST_RLS_URL for disposable PostgreSQL RLS evidence")
    parsed = make_url(url)
    if not parsed.drivername.startswith("postgresql") or not (parsed.database or "").endswith(
        "_test"
    ):
        pytest.fail("PANCHANG_TEST_RLS_URL must target a PostgreSQL *_test database")
    return url


@pytest.fixture(scope="module")
def migrated_rls(rls_url: str) -> str:
    engine = create_engine(_sync_url(rls_url), connect_args={"connect_timeout": 5})
    try:
        with engine.begin() as connection:
            config = Config(str(API_ROOT / "alembic.ini"))
            config.set_main_option("script_location", str(API_ROOT / "alembic"))
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
    finally:
        engine.dispose()
    return rls_url


def test_user_owned_tables_have_forced_rls_and_owner_policies(migrated_rls: str) -> None:
    engine = create_engine(_sync_url(migrated_rls), connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity "
                    "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = current_schema() AND c.relname = ANY(:tables)"
                ),
                {"tables": list(EXPECTED_POLICIES)},
            ).all()
            assert {row.relname for row in rows} == EXPECTED_POLICIES
            assert all(row.relrowsecurity and row.relforcerowsecurity for row in rows)

            policies = (
                connection.execute(
                    text(
                        "SELECT tablename FROM pg_policies "
                        "WHERE schemaname = current_schema() AND policyname LIKE 'rls_%_owner'"
                    )
                )
                .scalars()
                .all()
            )
            assert set(policies) >= EXPECTED_POLICIES
    finally:
        engine.dispose()


def test_rls_contract_lists_only_explicit_user_owned_tables() -> None:
    from importlib.util import module_from_spec, spec_from_file_location

    path = API_ROOT / "alembic/versions/0005_user_data_rls.py"
    spec = spec_from_file_location("user_data_rls", path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    assert {table for table, _column in module._OWNED_TABLES} == EXPECTED_POLICIES
    assert {column for _table, column in module._OWNED_TABLES} >= {
        "user_id",
        "owner_user_id",
        "subject_id",
    }


def test_rls_hides_other_users_and_rejects_cross_owner_insert(migrated_rls: str) -> None:
    engine = create_engine(_sync_url(migrated_rls), connect_args={"connect_timeout": 5})
    first_user, second_user = str(uuid4()), str(uuid4())
    first_note, second_note = str(uuid4()), str(uuid4())
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO users (id, auth_subject_ref, display_name, roles) VALUES "
                    "(:id, :subject, :name, CAST(:roles AS jsonb))"
                ),
                [
                    {
                        "id": first_user,
                        "subject": f"rls:{first_user}",
                        "name": "First",
                        "roles": json.dumps([]),
                    },
                    {
                        "id": second_user,
                        "subject": f"rls:{second_user}",
                        "name": "Second",
                        "roles": json.dumps([]),
                    },
                ],
            )
            connection.execute(
                text(
                    "INSERT INTO notes (id, owner_user_id, category, body, tags) VALUES "
                    "(:id, :owner, 'test', :body, CAST(:tags AS jsonb))"
                ),
                [
                    {
                        "id": first_note,
                        "owner": first_user,
                        "body": "first private note",
                        "tags": json.dumps([]),
                    },
                    {
                        "id": second_note,
                        "owner": second_user,
                        "body": "second private note",
                        "tags": json.dumps([]),
                    },
                ],
            )
            connection.execute(
                text("SELECT set_config('app.user_id', :id, false)"), {"id": first_user}
            )
            visible = connection.execute(text("SELECT id FROM notes ORDER BY id")).scalars().all()
            assert visible == [first_note]

            with pytest.raises(Exception, match=r"row-level security|violates row-level"):
                connection.execute(
                    text(
                        "INSERT INTO notes (id, owner_user_id, category, body, tags) VALUES "
                        "(:id, :owner, 'test', 'should fail', CAST(:tags AS jsonb))"
                    ),
                    {"id": str(uuid4()), "owner": second_user, "tags": json.dumps([])},
                )
    finally:
        # A fresh test database is preferred; cleanup is best effort and is
        # performed with RLS disabled only for these unique fixture rows.
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE notes DISABLE ROW LEVEL SECURITY"))
            connection.execute(
                text("DELETE FROM notes WHERE id IN (:first, :second)"),
                {
                    "first": first_note,
                    "second": second_note,
                },
            )
            connection.execute(
                text("DELETE FROM users WHERE id IN (:first, :second)"),
                {
                    "first": first_user,
                    "second": second_user,
                },
            )
            connection.execute(text("ALTER TABLE notes ENABLE ROW LEVEL SECURITY"))
            connection.execute(text("ALTER TABLE notes FORCE ROW LEVEL SECURITY"))
        engine.dispose()
