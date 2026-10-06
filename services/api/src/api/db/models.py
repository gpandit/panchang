"""ORM models for the temple domain.

The nested value objects (location, aarti schedule, events) are stored as JSON(B)
columns rather than child tables: they are always read and written as a whole with
the parent ``TempleConfig`` and never queried individually, so a document-style
column keeps the mapping a faithful 1:1 with the Pydantic models.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from api.db.base import JSON_VARIANT, Base


class TempleRow(Base):
    __tablename__ = "temples"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    name_dev: Mapped[str] = mapped_column(String, nullable=False)
    tagline: Mapped[str] = mapped_column(String, nullable=False, default="")
    location: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False)
    aarti: Mapped[list[dict[str, Any]]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    events: Mapped[list[dict[str, Any]]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_by: Mapped[str | None] = mapped_column(String, nullable=True)


class TempleAdminRow(Base):
    __tablename__ = "temple_admin_accounts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    salt: Mapped[str] = mapped_column(String, nullable=False)
    temple_id: Mapped[str] = mapped_column(
        String, ForeignKey("temples.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# Import v3 models after the legacy temple models so Alembic sees one complete
# metadata graph while existing temple callers keep their historical classes.
from api.db.v3_models import *  # noqa: E402,F401,F403
