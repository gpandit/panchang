"""Alembic migration environment (synchronous, psycopg).

The database URL is pulled from the application settings (``API_DATABASE_URL``) so
migrations always run against the same database the API uses. All ORM models are
imported via ``api.db`` so ``target_metadata`` is complete for autogenerate.
"""

from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy.engine import Connection

from alembic import context
from api.db import Base, get_engine

# Import models for their side effect of registering tables on Base.metadata.
from api.db import models as _models  # noqa: F401
from api.db.session import _sync_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a live DB connection (`alembic upgrade --sql`)."""
    from api.settings import get_settings

    context.configure(
        url=_sync_url(get_settings().database_url),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live connection using the app's engine."""
    # Supplying a connection through ``Config.attributes`` makes migration
    # smoke tests deterministic and lets callers share an already configured
    # connection/transaction.  Production still uses the application engine
    # below, so Alembic and the API retain one database URL contract.
    connection = config.attributes.get("connection")
    if connection is not None:
        _run_migrations(connection)
        return

    engine = get_engine()
    with engine.connect() as connection:
        _run_migrations(connection)


def _run_migrations(connection: Connection) -> None:
    """Configure and execute migrations on a SQLAlchemy connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
