"""Async SQLAlchemy session/engine wiring for the Content module.

Mirrors the pattern from `api.users.db`. Production uses Postgres; tests use
in-memory SQLite via `make_session_factory("sqlite+aiosqlite://")`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from api.content.models import ContentBase


def make_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, future=True)


def make_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    engine = make_engine(database_url)
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_models(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(ContentBase.metadata.create_all)


async def get_session(factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with factory() as session:
        yield session
