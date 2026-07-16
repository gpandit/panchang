"""Database layer — SQLAlchemy engines, session factories, ORM models, repositories.

Two engines share one ``database_url``:

- **sync** (psycopg3) backs the low-traffic temple domain and is what Alembic runs
  migrations through;
- **async** (:func:`get_session` dependency + :class:`Repository`) is the spine the
  marketplace modules build on — every marketplace request handler gets an
  ``AsyncSession`` injected.

Schema is owned by Alembic (``services/api/alembic``); ``alembic upgrade head`` is the
only thing that creates tables in staging/prod. ``Base.metadata.create_all`` is used
solely by the test suite against in-memory SQLite.
"""

from api.db.base import Base
from api.db.repository import Repository
from api.db.session import (
    async_session_scope,
    get_async_engine,
    get_engine,
    get_session,
    reset_async_engine,
    reset_engine,
    session_scope,
)

__all__ = [
    "Base",
    "Repository",
    "async_session_scope",
    "get_async_engine",
    "get_engine",
    "get_session",
    "reset_async_engine",
    "reset_engine",
    "session_scope",
]
