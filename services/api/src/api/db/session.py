"""Synchronous SQLAlchemy engine + session factory.

The engine is built lazily from ``settings.database_url`` and memoised, so it picks
up whatever ``API_DATABASE_URL`` is configured at first use (Postgres in staging/prod,
in-memory SQLite under test). ``reset_engine`` exists so tests can swap the URL.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api.settings import get_settings

_engine: Engine | None = None
_Session: sessionmaker[Session] | None = None


def _build_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        # A single shared in-memory database for the whole test session.
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
    return create_engine(url, pool_pre_ping=True, future=True)


def get_engine() -> Engine:
    """Return the process-wide engine, building it on first use."""
    global _engine, _Session
    if _engine is None:
        _engine = _build_engine(get_settings().database_url)
        _Session = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
    return _engine


def _get_sessionmaker() -> sessionmaker[Session]:
    get_engine()  # ensures _Session is initialised
    assert _Session is not None
    return _Session


def reset_engine() -> None:
    """Dispose the current engine and force a rebuild on next use (test hook)."""
    global _engine, _Session
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _Session = None


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional session; commit on success, roll back on error."""
    session = _get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
