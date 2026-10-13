"""Opt-in PCS evidence against disposable PostgreSQL and Redis services.

The regular Panchang suite uses in-memory stores.  These tests require explicit
``PANCHANG_TEST_POSTGRES_URL`` and ``PANCHANG_TEST_REDIS_URL`` values so a local
database or Redis instance is never selected accidentally.  PostgreSQL is
migrated through the API's existing Alembic chain, then the PCS uses the
existing ``panchang_days`` table through its concrete repository adapter.
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from psycopg import connect
from redis import Redis
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from panchang.app import PostgresCacheRepository
from panchang.cache import (
    ENGINE_VERSION,
    PostgresPanchangDayStore,
    RedisKeyLock,
    RedisStore,
    cache_key_for,
)
from panchang.compute import compute_panchang
from panchang.models import PanchangRequest

PCS_ROOT = Path(__file__).parents[1]
API_ROOT = PCS_ROOT.parent / "api"


@pytest.fixture(scope="module")
def postgres_url() -> str:
    url = os.environ.get("PANCHANG_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("set PANCHANG_TEST_POSTGRES_URL to a disposable PostgreSQL *_test DB")
    parsed = make_url(url)
    if not parsed.drivername.startswith("postgresql") or not (parsed.database or "").endswith(
        "_test"
    ):
        pytest.fail("PANCHANG_TEST_POSTGRES_URL must target a PostgreSQL *_test database")
    return url


@pytest.fixture(scope="module")
def migrated_postgres(postgres_url: str) -> str:
    """Apply the existing migrations without dropping or recreating the table."""
    engine = create_engine(
        postgres_url,
        connect_args={"connect_timeout": 5},
    )
    try:
        with engine.connect() as connection:
            config = Config(str(API_ROOT / "alembic.ini"))
            config.set_main_option("script_location", str(API_ROOT / "alembic"))
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            columns = {
                row[0]
                for row in connection.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = 'panchang_days'"
                    )
                )
            }
            assert {
                "date",
                "grid_lat",
                "grid_lon",
                "timezone",
                "ayanamsa",
                "scheme",
                "engine_version",
                "payload",
            } <= columns
    finally:
        engine.dispose()
    return postgres_url


def _unique_request() -> PanchangRequest:
    """Create a valid, very unlikely-to-collide durable cache identity."""
    seed = uuid4().int
    day = date(2035, 1, 1) + timedelta(days=(seed >> 32) % 3650)
    lat_grid = -80.0 + (seed % 1_600) / 10
    lon_grid = -170.0 + ((seed >> 12) % 3_400) / 10
    return PanchangRequest(
        date=day,
        lat=lat_grid + 0.01,
        lon=lon_grid + 0.01,
        tz="Asia/Kolkata",
    )


def _delete_postgres_fixture(url: str, request: PanchangRequest) -> None:
    identity = cache_key_for(request)
    connection = connect(
        url.replace("postgresql+psycopg://", "postgresql://", 1),
        autocommit=True,
    )
    try:
        connection.execute(
            """
            DELETE FROM panchang_days
            WHERE date = %s AND grid_lat = %s AND grid_lon = %s
              AND timezone = %s AND ayanamsa = %s AND scheme = %s
              AND engine_version = %s
            """,
            (
                identity.date,
                identity.lat_grid,
                identity.lon_grid,
                identity.tz,
                identity.ayanamsa,
                identity.month_scheme,
                identity.engine_version,
            ),
        )
    finally:
        connection.close()


def test_real_postgres_serialized_panchang_cache_readback(
    migrated_postgres: str,
) -> None:
    request = _unique_request()
    identity = cache_key_for(request)
    canonical_request = request.model_copy(
        update={"lat": identity.lat_grid, "lon": identity.lon_grid}
    )
    result = compute_panchang(canonical_request)
    key = identity.as_string()
    repository = PostgresCacheRepository(migrated_postgres)
    store = PostgresPanchangDayStore(repository)
    try:
        store.put(key, ENGINE_VERSION, result)
        assert store.get(key) == (ENGINE_VERSION, result)
    finally:
        repository.close()
        _delete_postgres_fixture(migrated_postgres, request)


def test_real_redis_roundtrip_ttl_and_cross_client_lock() -> None:
    url = os.environ.get("PANCHANG_TEST_REDIS_URL")
    if not url:
        pytest.skip("set PANCHANG_TEST_REDIS_URL to an isolated Redis service")

    client = Redis.from_url(url, socket_connect_timeout=5, socket_timeout=5)
    contender = Redis.from_url(url, socket_connect_timeout=5, socket_timeout=5)
    key = f"panchang:integration:{uuid4()}"
    store = RedisStore(client)
    payload = compute_panchang(_unique_request())
    try:
        assert client.ping()
        store.set(key, ENGINE_VERSION, payload, 30)
        assert store.get(key) == (ENGINE_VERSION, payload)
        assert 0 < client.ttl(key) <= 30

        first = RedisKeyLock(client, lease_seconds=30, wait_seconds=1)
        second = RedisKeyLock(contender, lease_seconds=30, wait_seconds=1)
        with first(key) as assert_first_owned:
            assert_first_owned()
            with pytest.raises(TimeoutError, match="unavailable"):
                with second(key):
                    pytest.fail("second Redis client acquired a held cache lock")

        # Releasing from the first client must make the lock available to the
        # independent second client, proving contention and release semantics.
        with second(key) as assert_second_owned:
            assert_second_owned()
    finally:
        client.delete(key, f"{key}:lock")
        contender.delete(f"{key}:lock")
        client.close()
        contender.close()
