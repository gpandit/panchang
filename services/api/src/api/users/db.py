"""Async SQLAlchemy session/engine wiring for the Users module.

Production uses Postgres (`API_DATABASE_URL`, asyncpg). Tests use an
in-memory SQLite database via `make_session_factory("sqlite+aiosqlite://")`
so the module can be exercised without a running Postgres instance.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base shared by all Users-module ORM models."""


def make_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, future=True)


def make_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    engine = make_engine(database_url)
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_models(engine: AsyncEngine) -> None:
    """Create all tables. Production uses Alembic migrations; this is the
    fast path for tests and local dev bootstrapping."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session(factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with factory() as session:
        yield session
