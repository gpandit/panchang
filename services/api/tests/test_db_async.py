"""Smoke tests for the async persistence spine (F1).

Proves a row inserts and reads back through an ``AsyncSession`` and the generic
:class:`Repository`, and that the :func:`get_session` FastAPI dependency yields a
working, transactional session. A throwaway declarative base keeps the app's
``Base.metadata`` (and therefore Alembic autogenerate) untouched.
"""

from __future__ import annotations

import pytest
from sqlalchemy import String, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from api.db import Repository, get_async_engine, get_session, reset_async_engine


class _SmokeBase(DeclarativeBase):
    pass


class _Widget(_SmokeBase):
    __tablename__ = "smoke_widgets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)


class _WidgetRepository(Repository[_Widget]):
    model = _Widget

    async def by_name(self, name: str) -> _Widget | None:
        result = await self.session.execute(select(_Widget).where(_Widget.name == name))
        return result.scalar_one_or_none()


@pytest.fixture
async def _smoke_schema():
    """Create the throwaway table on the async engine, drop it afterwards."""
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(_SmokeBase.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(_SmokeBase.metadata.drop_all)
    await reset_async_engine()


async def test_async_session_inserts_and_reads_via_repository(_smoke_schema):
    # Anext the dependency generator the way FastAPI would.
    gen = get_session()
    session = await gen.__anext__()
    repo = _WidgetRepository(session)

    await repo.add(_Widget(id="w1", name="kalash"))

    assert await repo.count() == 1
    fetched = await repo.get("w1")
    assert fetched is not None and fetched.name == "kalash"
    assert (await repo.by_name("kalash")).id == "w1"

    # Closing the generator triggers the dependency's commit + close.
    await gen.aclose()


async def test_get_session_rolls_back_on_error(_smoke_schema):
    gen = get_session()
    session = await gen.__anext__()
    await _WidgetRepository(session).add(_Widget(id="w2", name="diya"))

    # Simulate a handler raising: the dependency must roll the transaction back.
    with pytest.raises(RuntimeError):
        await gen.athrow(RuntimeError("boom"))

    # A fresh session sees nothing — the failed unit of work was discarded.
    verify_gen = get_session()
    verify_session = await verify_gen.__anext__()
    assert await _WidgetRepository(verify_session).get("w2") is None
    await verify_gen.aclose()


async def test_delete_by_id_reports_removal(_smoke_schema):
    gen = get_session()
    session = await gen.__anext__()
    repo = _WidgetRepository(session)
    await repo.add(_Widget(id="w3", name="bell"))

    assert await repo.delete_by_id("w3") is True
    assert await repo.delete_by_id("missing") is False
    await gen.aclose()
