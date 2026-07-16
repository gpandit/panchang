"""SQLAlchemy engines + session factories — synchronous and asynchronous.

Both engines are built lazily from ``settings.database_url`` and memoised, so they
pick up whatever ``API_DATABASE_URL`` is configured at first use (Postgres in
staging/prod, in-memory SQLite under test). ``reset_engine`` / ``reset_async_engine``
exist so tests can swap the URL.

The **sync** engine backs the low-traffic temple domain and is also what Alembic runs
migrations through. The **async** engine + :func:`get_session` FastAPI dependency are
the spine the marketplace modules build on — every marketplace request gets an
``AsyncSession`` injected, scoped to the request and committed/rolled-back for it.

Driver note: the project standardises on psycopg3, whose ``postgresql+psycopg://`` DSN
serves *both* the sync and async engines, so the single ``database_url`` needs no
translation for Postgres. Only the SQLite test URL is rewritten to its async driver
(``sqlite+aiosqlite://``).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api.settings import get_settings

_engine: Engine | None = None
_Session: sessionmaker[Session] | None = None

_async_engine: AsyncEngine | None = None
_AsyncSession: async_sessionmaker[AsyncSession] | None = None


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


def _async_url(url: str) -> str:
    """Translate the configured sync DSN to its async-driver equivalent.

    ``postgresql+psycopg://`` is already async-capable (psycopg3), so it passes
    through untouched; a bare ``postgresql://`` gets the psycopg driver pinned. The
    in-memory/file SQLite test URL is switched to the aiosqlite driver.
    """
    if url.startswith("sqlite+"):
        return url
    if url.startswith("sqlite"):
        return url.replace("sqlite", "sqlite+aiosqlite", 1)
    if url.startswith("postgresql+"):
        return url
    if url.startswith("postgresql"):
        return url.replace("postgresql", "postgresql+psycopg", 1)
    return url


def _build_async_engine(url: str) -> AsyncEngine:
    if url.startswith("sqlite"):
        # Mirror the sync engine: one shared in-memory DB across all connections.
        return create_async_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
    return create_async_engine(url, pool_pre_ping=True, future=True)


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


# ── Async engine / session (the marketplace spine) ────────────────────────────


def get_async_engine() -> AsyncEngine:
    """Return the process-wide async engine, building it on first use."""
    global _async_engine, _AsyncSession
    if _async_engine is None:
        _async_engine = _build_async_engine(_async_url(get_settings().database_url))
        _AsyncSession = async_sessionmaker(
            bind=_async_engine, expire_on_commit=False, autoflush=False
        )
    return _async_engine


def _get_async_sessionmaker() -> async_sessionmaker[AsyncSession]:
    get_async_engine()  # ensures _AsyncSession is initialised
    assert _AsyncSession is not None
    return _AsyncSession


async def reset_async_engine() -> None:
    """Dispose the async engine and force a rebuild on next use (test hook)."""
    global _async_engine, _AsyncSession
    if _async_engine is not None:
        await _async_engine.dispose()
    _async_engine = None
    _AsyncSession = None


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yield a request-scoped ``AsyncSession``.

    Commits when the request handler returns cleanly and rolls back on any raised
    exception, so handlers never have to manage the transaction boundary themselves::

        @router.get("/...")
        async def handler(session: Annotated[AsyncSession, Depends(get_session)]):
            ...
    """
    session = _get_async_sessionmaker()()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@asynccontextmanager
async def async_session_scope() -> AsyncIterator[AsyncSession]:
    """Transactional async session for use outside the request cycle (workers, seeds)."""
    session = _get_async_sessionmaker()()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
