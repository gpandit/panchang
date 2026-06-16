"""Thin async repository pattern — the persistence primitive marketplace modules share.

A :class:`Repository` wraps an :class:`~sqlalchemy.ext.asyncio.AsyncSession` and a single
ORM model, exposing the handful of CRUD primitives every domain module needs (get by id,
add, list, delete) without hiding SQLAlchemy: domain repositories subclass this and add
their own query methods using ``self.session`` directly.

Deliberately minimal. It does **not** own the transaction — the session's lifecycle (and
the commit/rollback boundary) belongs to :func:`api.db.session.get_session`, so a single
request can coordinate writes across several repositories in one transaction. ``add`` and
``delete`` therefore ``flush`` (to surface integrity errors and populate defaults/PKs)
rather than ``commit``.

Example::

    class PanditRepository(Repository[PanditRow]):
        model = PanditRow

        async def by_slug(self, slug: str) -> PanditRow | None:
            result = await self.session.execute(
                select(PanditRow).where(PanditRow.slug == slug)
            )
            return result.scalar_one_or_none()
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.base import Base


class Repository[ModelT: Base]:
    """Generic async CRUD repository over a single ORM model.

    Subclasses set the ``model`` class attribute (or pass ``model=`` to the base
    constructor) and may add domain-specific query methods. Instances are cheap and
    request-scoped — construct one per session.
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession, model: type[ModelT] | None = None) -> None:
        self.session = session
        if model is not None:
            self.model = model
        if not hasattr(self, "model"):
            raise TypeError(
                f"{type(self).__name__} must set a `model` class attribute "
                "or be constructed with `model=`."
            )

    async def get(self, id_: Any) -> ModelT | None:
        """Return the row with this primary key, or ``None``."""
        return await self.session.get(self.model, id_)

    async def add(self, obj: ModelT) -> ModelT:
        """Stage ``obj`` for insert and flush so defaults/PKs are populated."""
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def list(
        self, *, limit: int | None = None, offset: int | None = None
    ) -> Sequence[ModelT]:
        """Return rows, optionally paginated (no implicit ordering)."""
        stmt = select(self.model)
        if offset is not None:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self) -> int:
        """Return the total row count for the model."""
        result = await self.session.execute(select(func.count()).select_from(self.model))
        return int(result.scalar_one())

    async def delete(self, obj: ModelT) -> None:
        """Delete a loaded instance and flush."""
        await self.session.delete(obj)
        await self.session.flush()

    async def delete_by_id(self, id_: Any) -> bool:
        """Delete the row with this primary key; return whether one was removed."""
        obj = await self.get(id_)
        if obj is None:
            return False
        await self.delete(obj)
        return True
