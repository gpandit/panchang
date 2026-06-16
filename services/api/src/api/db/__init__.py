"""Database layer — SQLAlchemy engine, session factory, ORM models.

The API gateway persists temple configs and temple-admin accounts here. Everything
is synchronous (psycopg3); the handful of temple endpoints are low-traffic admin /
signage reads, so a blocking session per request is more than adequate and keeps the
store API — and the test suite — synchronous.

Schema is owned by Alembic (``services/api/alembic``); ``alembic upgrade head`` is the
only thing that creates tables in staging/prod. ``Base.metadata.create_all`` is used
solely by the test suite against in-memory SQLite.
"""

from api.db.base import Base
from api.db.session import get_engine, reset_engine, session_scope

__all__ = ["Base", "get_engine", "reset_engine", "session_scope"]
