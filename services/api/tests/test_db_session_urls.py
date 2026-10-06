"""Cross-driver URL normalization tests for the shared DB setting."""

from __future__ import annotations

from api.db.session import _async_url, _sync_url


def test_async_url_normalizes_sqlite_drivers() -> None:
    assert _async_url("sqlite://") == "sqlite+aiosqlite://"
    assert _async_url("sqlite+pysqlite:///:memory:") == "sqlite+aiosqlite:///:memory:"
    assert _sync_url("sqlite+aiosqlite:///:memory:") == "sqlite:///:memory:"


def test_async_and_sync_url_normalize_postgres_drivers() -> None:
    configured = "postgresql://pandit:example-password@localhost:5432/pandit_dev"
    expected = "postgresql+psycopg://pandit:example-password@localhost:5432/pandit_dev"
    assert _async_url(configured) == expected
    assert (
        _sync_url("postgresql+asyncpg://pandit:example-password@localhost:5432/pandit_dev")
        == expected
    )
    assert (
        _async_url("postgresql+psycopg2://pandit:example-password@localhost:5432/pandit_dev")
        == expected
    )
    assert _sync_url("postgres://pandit:example-password@localhost:5432/pandit_dev") == expected
