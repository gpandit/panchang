"""Opt-in real-service evidence (requires disposable *_test PostgreSQL and Redis).

No service is inferred from API_DATABASE_URL: the ordinary suite remains SQLite-only.
CI sets both explicit URLs and runs this file separately with -s for observations.
"""

from __future__ import annotations

import os
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import pytest
from alembic.config import Config
from redis import Redis
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from alembic import command
from api.cache import RedisCache
from api.db.session import _async_url, _sync_url
from api.db.v3_models import OutboxEventRow, UserRow
from api.outbox import OutboxRepository

API_ROOT = Path(__file__).parents[1]


@pytest.fixture(scope="module")
def postgres_url() -> str:
    url = os.environ.get("PANCHANG_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("set PANCHANG_TEST_POSTGRES_URL to a disposable PostgreSQL/PostGIS *_test DB")
    parsed = make_url(url)
    if not parsed.drivername.startswith("postgresql") or not (parsed.database or "").endswith(
        "_test"
    ):
        pytest.fail("PANCHANG_TEST_POSTGRES_URL must target a PostgreSQL *_test database")
    return url


@pytest.fixture(scope="module")
def migrated_postgres(postgres_url: str) -> str:
    # Alembic's injected connection avoids changing the SQLite setting used by
    # unrelated tests. A dedicated CI service DB is fresh for each job.
    engine = create_engine(_sync_url(postgres_url), connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as connection:
            config = Config(str(API_ROOT / "alembic.ini"))
            config.set_main_option("script_location", str(API_ROOT / "alembic"))
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            assert connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one() == ("0003_s005_outbox_idempotency")
            assert connection.execute(text("SELECT PostGIS_Version()")).scalar_one()
            assert (
                connection.execute(
                    text(
                        "SELECT udt_name FROM information_schema.columns "
                        "WHERE table_name = 'locations' AND column_name = 'point'"
                    )
                ).scalar_one()
                == "geography"
            )
    finally:
        engine.dispose()
    return postgres_url


@pytest.mark.asyncio
async def test_postgres_user_outbox_transaction_readback_and_query_observation(
    migrated_postgres: str,
) -> None:
    engine = create_async_engine(_async_url(migrated_postgres), pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    user_id = str(uuid4())
    event_id = str(uuid4())
    try:
        async with sessions() as session:
            user = UserRow(
                id=user_id,
                auth_subject_ref=f"integration:{user_id}",
                display_name="Integration fixture",
                roles=["patron"],
            )
            session.add(user)
            await session.flush()
            event = await OutboxRepository(session).enqueue(
                event_id=event_id,
                aggregate_type="user",
                aggregate_id=user_id,
                event_type="user.created",
                payload_ref=f"fixture://{user_id}",
            )
            assert event.state == "pending"
            await session.commit()

        # A second connection proves the transaction is durable and the JSONB
        # field and event envelope survive PostgreSQL serialization.
        async with sessions() as reader:
            loaded = await reader.get(UserRow, user_id)
            persisted_event = await reader.get(OutboxEventRow, event_id)
            assert loaded is not None and loaded.roles == ["patron"]
            assert persisted_event is not None
            assert persisted_event.aggregate_id == user_id
            assert persisted_event.payload_ref == f"fixture://{user_id}"
            assert persisted_event.state == "pending"

            stmt = select(OutboxEventRow.id).where(
                OutboxEventRow.aggregate_type == "user",
                OutboxEventRow.aggregate_id == user_id,
            )
            observations_ms = []
            for _ in range(5):
                start = perf_counter()
                assert (await reader.execute(stmt)).scalar_one() == event_id
                observations_ms.append((perf_counter() - start) * 1000)
            plan = await reader.execute(
                text(
                    "EXPLAIN SELECT id FROM outbox_events "
                    "WHERE aggregate_type = :kind AND aggregate_id = :aggregate_id"
                ),
                {"kind": "user", "aggregate_id": user_id},
            )
            print(
                "Postgres fixture outbox lookup (5 samples, includes client/CI noise): "
                f"min={min(observations_ms):.2f}ms max={max(observations_ms):.2f}ms; "
                f"plan={plan.scalars().first()} — not a production p95/SLO measurement"
            )
    finally:
        async with sessions() as cleanup:
            await cleanup.execute(
                OutboxEventRow.__table__.delete().where(OutboxEventRow.id == event_id)
            )
            await cleanup.execute(UserRow.__table__.delete().where(UserRow.id == user_id))
            await cleanup.commit()
        await engine.dispose()


def test_redis_roundtrip_cache_ttl_and_per_key_lock() -> None:
    url = os.environ.get("PANCHANG_TEST_REDIS_URL")
    if not url:
        pytest.skip("set PANCHANG_TEST_REDIS_URL to an isolated Redis service")
    client = Redis.from_url(url, socket_connect_timeout=5, socket_timeout=5)
    key = f"panchang:integration:{uuid4()}"
    cache = RedisCache(client, default_ttl=30)
    try:
        assert client.ping()
        assert cache.get(key) == (None, False)
        payload = {"date": "2026-10-07", "flags": ["fixture"]}
        cache.set(key, payload)
        assert cache.get(key) == (payload, True)
        assert 0 < client.ttl(key) <= 30

        # Two independent clients contend for the same Redis key. This is a
        # coordination seam, not proof that the gateway uses Redis in production.
        contender = Redis.from_url(url, socket_connect_timeout=5, socket_timeout=5)
        first = cache.lock(key)
        second = RedisCache(contender, default_ttl=30).lock(key)
        try:
            assert first.acquire(blocking=False)
            assert not second.acquire(blocking=False)
            first.release()
            assert second.acquire(blocking=False)
            second.release()
        finally:
            if first.owned():
                first.release()
            if second.owned():
                second.release()
            contender.close()
    finally:
        client.delete(key, f"{key}:lock")
        client.close()
