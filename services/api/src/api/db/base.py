"""Declarative base + the cross-dialect JSON column type.

``JSON_VARIANT`` is JSONB on PostgreSQL (staging/prod) and plain JSON on SQLite
(the test suite), so the same models work in both places.
"""

from __future__ import annotations

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase

# JSONB where available (Postgres), falling back to JSON text on SQLite.
JSON_VARIANT = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
