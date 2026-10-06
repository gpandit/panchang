"""Portable checks for the v3 migration/model foundation.

These tests intentionally use SQLite for fast CI.  PostgreSQL-only geography and
booking range enforcement are represented by explicit dialect fallbacks and the
PostgreSQL exclusion DDL in ``api.db.v3_models``.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.db import Base
from api.db import models as _models  # noqa: F401
from api.db.v3_models import (
    BookingRow,
    LedgerJournalRow,
    PanchangDayRow,
    UserRow,
)


@pytest.fixture
def v3_session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_v3_schema_contains_dependency_ordered_domains(v3_session: Session) -> None:
    names = set(inspect(v3_session.bind).get_table_names())
    assert {
        "users",
        "vault_refs",
        "panchang_days",
        "festival_rules",
        "reminders",
        "subscriptions",
        "provider_accounts",
        "ledger_journals",
        "bookings",
        "order_refs",
    } <= names


def test_sensitive_values_are_references_not_profile_columns() -> None:
    ordinary = {column.name for column in UserRow.__table__.columns}
    assert not ordinary.intersection({"date_of_birth", "time_of_birth", "place_of_birth", "kyc_document", "exact_address"})
    assert {"email_ref", "phone_ref", "auth_subject_ref"} <= ordinary


def test_booking_range_uses_postgres_timestamptz_range_and_integer_money() -> None:
    booking_ddl = str(
        CreateTable(BookingRow.__table__).compile(dialect=postgresql.dialect())
    )
    assert "TSTZRANGE" in booking_ddl
    assert "BIGINT" in str(LedgerJournalRow.__table__.c.debit_total_minor.type)


def test_panchang_cache_key_is_unique(v3_session: Session) -> None:
    first = PanchangDayRow(
        id="p1",
        date=date(2026, 1, 1),
        grid_lat=25,
        grid_lon=55,
        timezone="Asia/Dubai",
        ayanamsa="lahiri",
        scheme="amanta",
        engine_version="test",
        payload={"intervals": []},
    )
    second = PanchangDayRow(
        id="p2",
        date=date(2026, 1, 1),
        grid_lat=25,
        grid_lon=55,
        timezone="Asia/Dubai",
        ayanamsa="lahiri",
        scheme="amanta",
        engine_version="test",
        payload={"intervals": []},
    )
    v3_session.add_all([first, second])
    with pytest.raises(IntegrityError):
        v3_session.commit()


def test_journal_balance_and_booking_time_checks_are_portable(v3_session: Session) -> None:
    v3_session.add(
        LedgerJournalRow(
            id="j1",
            aggregate_ref="a1",
            currency="USD",
            status="posted",
            debit_total_minor=100,
            credit_total_minor=99,
        )
    )
    with pytest.raises(IntegrityError):
        v3_session.commit()

    v3_session.rollback()
    v3_session.add(
        BookingRow(
            id="b2",
            patron_id="u1",
            pandit_id="p1",
            service_id="s1",
            mode="in_person",
            starts_at=datetime(2026, 1, 1, 10, tzinfo=UTC),
            ends_at=datetime(2026, 1, 1, 11, tzinfo=UTC),
            state="confirmed",
            quote_snapshot={},
            policy_snapshot={},
        )
    )
    v3_session.commit()
    v3_session.add(
        BookingRow(
            id="b3",
            patron_id="u2",
            pandit_id="p1",
            service_id="s1",
            mode="in_person",
            starts_at=datetime(2026, 1, 1, 10, 30, tzinfo=UTC),
            ends_at=datetime(2026, 1, 1, 11, 30, tzinfo=UTC),
            state="requested",
            quote_snapshot={},
            policy_snapshot={},
        )
    )
    with pytest.raises(IntegrityError):
        v3_session.commit()

    v3_session.rollback()
    v3_session.add(
        BookingRow(
            id="b1",
            patron_id="u1",
            pandit_id="p1",
            service_id="s1",
            mode="in_person",
            starts_at=datetime(2026, 1, 2, tzinfo=UTC),
            ends_at=datetime(2026, 1, 1, tzinfo=UTC),
            state="requested",
            quote_snapshot={},
            policy_snapshot={},
        )
    )
    with pytest.raises(IntegrityError):
        v3_session.commit()
