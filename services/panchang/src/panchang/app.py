"""FastAPI application — The Pandit Panchang Computation Service.

Internal service; never exposed directly to clients.
The API gateway calls this service via the configured PANCHANG_SERVICE_URL.

Routes:
  GET  /health            — liveness probe
  POST /compute           — compute a single PanchangDay
  POST /compute/month     — compute a full calendar month
  POST /warm              — trigger cache warm for a location
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Any, cast

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from psycopg import Connection, connect
from psycopg.types.json import Jsonb
from pydantic import BaseModel
from redis import Redis

from panchang.cache import (
    PanchangCache,
    PostgresPanchangDayStore,
    RedisClient,
    RedisKeyLock,
    RedisLockClient,
    RedisStore,
    SerializedPanchangRepository,
)
from panchang.compute import compute_panchang
from panchang.models import Ayanamsa, MonthScheme, PanchangRequest
from panchang.settings import get_settings
from panchang.sunrise_policy import SunriseFallbackError

settings = get_settings()
cache: PanchangCache | None = None
if settings.environment == "development":
    cache = PanchangCache(
        compute=compute_panchang,
        ttl_seconds=settings.cache_ttl_seconds,
        grid_degrees=settings.cache_grid_degrees,
    )


class ProductionRedisClient(RedisClient, RedisLockClient):
    """Combined structural contract for the injected redis-py client."""


def _psycopg_url(url: str) -> str:
    """Accept SQLAlchemy's psycopg URL while using psycopg directly."""
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def _cache_identity(key: str) -> tuple[date, float, float, str, str, str, str]:
    """Decode the versioned cache key into the durable table identity.

    Time zones can contain colons (for example ``Etc/GMT+5``), so the five
    suffix fields are removed from the right rather than splitting by a fixed
    number of parts.
    """
    parts = key.split(":")
    if len(parts) < 10 or parts[0] != "panchang" or not parts[-1].startswith("grid="):
        raise ValueError("invalid Panchang cache key")
    engine_version = parts[1]
    day = date.fromisoformat(parts[2])
    lat = float(parts[3])
    lon = float(parts[4])
    timezone, ayanamsa, scheme, suffix_engine = parts[5:-4], parts[-4], parts[-3], parts[-2]
    timezone_name = ":".join(timezone)
    if suffix_engine != engine_version:
        raise ValueError("cache key engine versions differ")
    return day, lat, lon, timezone_name, ayanamsa, scheme, engine_version


class PostgresCacheRepository:
    """Small synchronous repository for the existing ``panchang_days`` table."""

    def __init__(self, database_url: str) -> None:
        self._connection: Connection[Any] = connect(_psycopg_url(database_url), autocommit=True)

    def get(self, key: str) -> tuple[str, str] | None:
        day, lat, lon, timezone, ayanamsa, scheme, engine_version = _cache_identity(key)
        row = self._connection.execute(
            """
            SELECT engine_version, payload FROM panchang_days
            WHERE date = %s AND grid_lat = %s AND grid_lon = %s AND timezone = %s
              AND ayanamsa = %s AND scheme = %s AND engine_version = %s
            """,
            (day, lat, lon, timezone, ayanamsa, scheme, engine_version),
        ).fetchone()
        if row is None:
            return None
        payload = row[1] if isinstance(row[1], str) else json.dumps(row[1])
        return str(row[0]), payload

    def put(self, key: str, engine_version: str, payload: str) -> None:
        day, lat, lon, timezone, ayanamsa, scheme, _ = _cache_identity(key)
        self._connection.execute(
            """
            INSERT INTO panchang_days
                (id, date, grid_lat, grid_lon, timezone, ayanamsa, scheme,
                 engine_version, payload)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (date, grid_lat, grid_lon, timezone, ayanamsa, scheme, engine_version)
            DO UPDATE SET payload = EXCLUDED.payload, updated_at = CURRENT_TIMESTAMP
            """,
            (
                str(uuid.uuid4()),
                day,
                lat,
                lon,
                timezone,
                ayanamsa,
                scheme,
                engine_version,
                Jsonb(json.loads(payload)),
            ),
        )

    def close(self) -> None:
        self._connection.close()


def configure_cache(
    redis_client: ProductionRedisClient,
    repository: SerializedPanchangRepository,
) -> None:
    """Inject shared clients before serving traffic outside local development."""
    global cache
    cache = PanchangCache(
        compute=compute_panchang,
        hot_store=RedisStore(redis_client),
        durable_store=PostgresPanchangDayStore(repository),
        key_lock=RedisKeyLock(redis_client),
        ttl_seconds=settings.cache_ttl_seconds,
        grid_degrees=settings.cache_grid_degrees,
    )


def _ready_cache() -> PanchangCache:
    if cache is None:
        raise HTTPException(status_code=503, detail="Panchang shared cache is not configured")
    return cache


def _ephemeris_ready() -> bool:
    path = Path(settings.ephemeris_path).expanduser()
    return path.is_dir() and all(
        (path / filename).is_file() for filename in ("semo_18.se1", "sepl_18.se1", "seas_18.se1")
    )


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    repository: PostgresCacheRepository | None = None
    redis_connection: Redis | None = None
    if settings.environment != "development":
        redis_connection = Redis.from_url(settings.redis_url)
        redis_connection.ping()
        repository = PostgresCacheRepository(settings.database_url)
        configure_cache(cast(ProductionRedisClient, redis_connection), repository)
    try:
        yield
    finally:
        if redis_connection is not None:
            redis_connection.close()
        if repository is not None:
            repository.close()


app = FastAPI(
    title="Panchang Computation Service",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)


@app.exception_handler(SunriseFallbackError)
async def sunrise_fallback_unavailable(
    _request: Request, exc: SunriseFallbackError
) -> JSONResponse:
    return JSONResponse(status_code=422, content={"reason": exc.reason, "flags": exc.flags})


class ComputeRequest(BaseModel):
    date: date
    lat: float
    lon: float
    tz: str
    ayanamsa: Ayanamsa = Ayanamsa.LAHIRI
    month_scheme: MonthScheme = MonthScheme.AMANTA


class MonthRequest(BaseModel):
    year: int
    month: int
    lat: float
    lon: float
    tz: str
    ayanamsa: Ayanamsa = Ayanamsa.LAHIRI
    month_scheme: MonthScheme = MonthScheme.AMANTA


@app.get("/health", tags=["meta"], include_in_schema=False)
async def health() -> dict[str, str]:
    _ready_cache()
    if not _ephemeris_ready():
        raise HTTPException(status_code=503, detail="Swiss Ephemeris data is unavailable")
    return {"status": "ok", "environment": settings.environment}


@app.post("/compute")
async def compute_single(req: ComputeRequest) -> JSONResponse:
    preq = PanchangRequest(
        date=req.date,
        lat=req.lat,
        lon=req.lon,
        tz=req.tz,
        ayanamsa=req.ayanamsa,
        month_scheme=req.month_scheme,
    )
    result = _ready_cache().get(preq)
    return JSONResponse(result.model_dump(mode="json", by_alias=True))


@app.post("/compute/month")
async def compute_month(req: MonthRequest) -> JSONResponse:
    import calendar as _cal
    from datetime import date as _date

    days_in_month = _cal.monthrange(req.year, req.month)[1]
    results = []
    for day in range(1, days_in_month + 1):
        d = _date(req.year, req.month, day)
        preq = PanchangRequest(
            date=d,
            lat=req.lat,
            lon=req.lon,
            tz=req.tz,
            ayanamsa=req.ayanamsa,
            month_scheme=req.month_scheme,
        )
        result = _ready_cache().get(preq)
        results.append(result.model_dump(mode="json", by_alias=True))

    return JSONResponse({"days": results})
