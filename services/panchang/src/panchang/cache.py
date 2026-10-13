"""Compute-and-cache layer for PanchangDay results (Step 1.4).

Architectural rule (north star #2): Panchang is precomputed and cached,
never calculated live on the device — and this layer must never change
*what* the engine computes, only *when*. A cache hit must always return a
value identical to a fresh compute for the same key.

Tiering
-------
- Redis (`RedisStore` / any `CacheStore`) is the hot read path: low-latency,
  TTL'd, holds the rolling warm horizon for popular locations.
- Postgres (`PanchangDayRepository` / `PostgresPanchangDayStore`) is the
  durable system of record: every computed PanchangDay is persisted there
  so it survives cache eviction/restarts and can be queried/audited. On a
  Redis miss we check Postgres before recomputing; a Postgres hit re-warms
  Redis. Only a miss in *both* triggers an engine compute.

Cache key
---------
A PanchangDay is fully determined by (date, location, ayanamsa, month
scheme, engine version). Locations are rounded to a coordinate grid so that
nearby users — e.g. people in the same city — share one cache entry instead
of each minting their own. See `LOCATION_GRID_DEGREES`.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from math import isfinite
from typing import Any, Protocol
from weakref import WeakValueDictionary
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from panchang.models import PanchangRequest, PanchangResult

# ──────────────────────────────────────────────────────────────────────────
# Engine version — bump whenever a change to the engine could change output
# for an existing key. Stored alongside every cached value so a version
# mismatch is treated as a miss, deterministically invalidating stale data
# without needing to enumerate or scan keys.
# ──────────────────────────────────────────────────────────────────────────
# v3 replaces flagged civil-midnight/noon placeholders with the named
# nearest-valid-latitude policy. Never reuse a v2 polar day's computed angas.
ENGINE_VERSION = "3"

# Location grid resolution, in degrees of latitude/longitude.
#
# 0.1° ≈ 11 km at the equator (less in longitude away from it). Sunrise/
# sunset times — the basis of the sunrise-to-sunrise Panchang day — shift by
# roughly 4 minutes per degree of longitude and vary slowly with latitude, so
# snapping to a 0.1° grid introduces at most ~30 seconds of drift in day-event
# timestamps for users sharing a cell. That is well within the precision the
# product displays (minute resolution) and far below the threshold that could
# flip an anga boundary across the requested date for all but a vanishing
# fraction of edge-case locations — those fall back to a fresh per-location
# compute on the rare occasions a boundary truly straddles the cell.
LOCATION_GRID_DEGREES = 0.1


def _grid_round(value: float, grid: float = LOCATION_GRID_DEGREES) -> float:
    return float(
        (Decimal(str(value)) / Decimal(str(grid))).quantize(0, rounding=ROUND_HALF_UP)
        * Decimal(str(grid))
    )


def _validate_grid(grid: float) -> float:
    if (
        isinstance(grid, bool)
        or not isinstance(grid, (int, float))
        or not isfinite(grid)
        or not 0 < grid <= 1
    ):
        raise ValueError("grid_degrees must be finite and in (0, 1]")
    # Stored coordinates in the existing v3 DB model have four decimal places.
    if grid != round(grid, 4):
        raise ValueError("grid_degrees must fit the four-decimal-place durable schema")
    return grid


def _validate_request(request: PanchangRequest) -> None:
    if (
        not all(isfinite(v) for v in (request.lat, request.lon))
        or not -90 <= request.lat <= 90
        or not -180 <= request.lon <= 180
    ):
        raise ValueError("latitude/longitude out of range or non-finite")
    if not request.tz or request.tz != request.tz.strip():
        raise ValueError("tz must be an IANA timezone")
    try:
        ZoneInfo(request.tz)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("tz must be an IANA timezone") from exc


@dataclass(frozen=True)
class CacheKey:
    """Identity of a cacheable PanchangDay computation.

    Equal keys are guaranteed to produce identical engine output, modulo the
    location-grid rounding documented above.
    """

    date: date
    lat_grid: float
    lon_grid: float
    tz: str
    ayanamsa: str
    month_scheme: str
    engine_version: str = ENGINE_VERSION
    grid_degrees: float = LOCATION_GRID_DEGREES

    def as_string(self) -> str:
        return (
            f"panchang:{self.engine_version}:{self.date.isoformat()}:"
            f"{self.lat_grid:.4f}:{self.lon_grid:.4f}:"
            f"{self.tz}:{self.ayanamsa}:{self.month_scheme}:{self.engine_version}"
            f":grid={self.grid_degrees:.4f}"
        )


def cache_key_for(
    request: PanchangRequest,
    *,
    grid_degrees: float = LOCATION_GRID_DEGREES,
    engine_version: str = ENGINE_VERSION,
) -> CacheKey:
    """Derive the cache key for a request, applying the location grid."""
    _validate_request(request)
    _validate_grid(grid_degrees)
    _validate_engine_version(engine_version)
    return CacheKey(
        date=request.date,
        lat_grid=max(-90.0, min(90.0, _grid_round(request.lat, grid_degrees))),
        lon_grid=max(-180.0, min(180.0, _grid_round(request.lon, grid_degrees))),
        tz=request.tz,
        ayanamsa=request.ayanamsa.value,
        month_scheme=request.month_scheme.value,
        engine_version=engine_version,
        grid_degrees=grid_degrees,
    )


# ──────────────────────────────────────────────────────────────────────────
# Store protocols — kept minimal and storage-agnostic so production can wire
# real Redis/Postgres clients while tests use simple in-memory fakes.
# ──────────────────────────────────────────────────────────────────────────


class CacheStore(Protocol):
    """Hot-path key/value store (Redis in production)."""

    def get(self, key: str) -> tuple[str, PanchangResult] | None:
        """Return (engine_version, result) for *key*, or None on miss."""
        ...

    def set(
        self, key: str, engine_version: str, result: PanchangResult, ttl_seconds: int
    ) -> None: ...


class PanchangDayRepository(Protocol):
    """Durable system of record (Postgres in production)."""

    def get(self, key: str) -> tuple[str, PanchangResult] | None: ...

    def put(self, key: str, engine_version: str, result: PanchangResult) -> None: ...


class RedisClient(Protocol):
    """Small subset of a synchronous redis-py client used by ``RedisStore``.

    Keeping the client injected means the service does not need to install or
    import redis in tests.  A redis-py ``Redis`` instance satisfies this
    protocol structurally.
    """

    def get(self, name: str) -> bytes | str | None: ...

    def set(self, name: str, value: str, *, ex: int) -> Any: ...


class SerializedPanchangRepository(Protocol):
    """Database-facing contract for a serialized Panchang result.

    An application repository can implement these two methods with its
    preferred Postgres driver/transaction layer.  The cache module therefore
    owns serialization and version semantics without depending on SQLAlchemy
    or a particular Postgres package.
    """

    def get(self, key: str) -> tuple[str, str] | None: ...

    def put(self, key: str, engine_version: str, payload: str) -> None: ...


class KeyLock(Protocol):
    """A context-managed per-key lock shared by every process using the durable store."""

    def __call__(self, key: str) -> Any: ...


class RedisLockClient(Protocol):
    def lock(self, name: str, *, timeout: int, blocking_timeout: int) -> Any: ...


class RedisKeyLock:
    """Injected redis-py lock adapter; timeout fails closed rather than computing unlocked.

    The lease must exceed the worst-case compute plus durable write duration.
    If that cannot be guaranteed, use a fencing-capable durable lock adapter.
    """

    def __init__(
        self, client: RedisLockClient, *, lease_seconds: int = 120, wait_seconds: int = 30
    ) -> None:
        self._client = client
        self._lease = _validate_ttl(lease_seconds)
        self._wait = _validate_ttl(wait_seconds)

    @contextmanager
    def __call__(self, key: str) -> Iterator[Callable[[], None]]:
        lock = self._client.lock(f"{key}:lock", timeout=self._lease, blocking_timeout=self._wait)
        if not lock.acquire():
            raise TimeoutError(f"Panchang cache lock unavailable: {key}")
        try:
            yield lambda: _assert_lock_owned(lock)
        finally:
            if lock.owned():
                lock.release()


def _assert_lock_owned(lock: Any) -> None:
    if not lock.owned():
        raise TimeoutError("Panchang cache lock lease expired")


def _validate_ttl(ttl_seconds: int) -> int:
    if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int) or ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be a positive integer")
    return ttl_seconds


def _validate_engine_version(engine_version: str) -> str:
    if (
        not isinstance(engine_version, str)
        or not engine_version
        or engine_version != engine_version.strip()
    ):
        raise ValueError("engine_version must be a non-empty string")
    return engine_version


def _decode_json_payload(payload: bytes | str) -> dict[str, Any]:
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    decoded = json.loads(payload)
    if not isinstance(decoded, dict):
        raise ValueError("cache payload must be a JSON object")
    return decoded


class InMemoryCacheStore:
    """Dict-backed `CacheStore` — stands in for Redis in tests/dev."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[str, PanchangResult]] = {}

    def get(self, key: str) -> tuple[str, PanchangResult] | None:
        return self._data.get(key)

    def set(self, key: str, engine_version: str, result: PanchangResult, ttl_seconds: int) -> None:
        _validate_ttl(ttl_seconds)
        # TTL is honoured by real Redis (EX=ttl_seconds); the in-memory fake
        # keeps entries for the lifetime of the process, which is sufficient
        # for tests and local dev.
        self._data[key] = (engine_version, result)


class InMemoryPanchangDayStore:
    """Dict-backed `PanchangDayRepository` — stands in for Postgres in tests."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[str, PanchangResult]] = {}

    def get(self, key: str) -> tuple[str, PanchangResult] | None:
        return self._data.get(key)

    def put(self, key: str, engine_version: str, result: PanchangResult) -> None:
        self._data[key] = (engine_version, result)


class RedisStore:
    """Serialized Redis adapter using an injected redis-compatible client."""

    def __init__(self, client: RedisClient) -> None:
        self._client = client

    def get(self, key: str) -> tuple[str, PanchangResult] | None:
        payload = self._client.get(key)
        if payload is None:
            return None
        record = _decode_json_payload(payload)
        engine_version = record.get("engine_version")
        result_payload = record.get("result")
        if not isinstance(engine_version, str) or not isinstance(result_payload, dict):
            raise ValueError("invalid Redis Panchang cache record")
        return engine_version, PanchangResult.model_validate(result_payload)

    def set(self, key: str, engine_version: str, result: PanchangResult, ttl_seconds: int) -> None:
        ttl_seconds = _validate_ttl(ttl_seconds)
        engine_version = _validate_engine_version(engine_version)
        payload = json.dumps(
            {
                "engine_version": engine_version,
                "result": result.model_dump(mode="json"),
            },
            separators=(",", ":"),
        )
        self._client.set(key, payload, ex=ttl_seconds)


class PostgresPanchangDayStore:
    """Serialized durable adapter over an injected Postgres repository.

    ``repository`` is intentionally just a persistence contract: production
    code can implement it with SQLAlchemy, psycopg, asyncpg-backed workers, or
    an existing repository layer.  A stale engine version is a miss, allowing
    a new compute to replace the record without a table scan.
    """

    def __init__(
        self,
        repository: SerializedPanchangRepository,
        *,
        engine_version: str = ENGINE_VERSION,
    ) -> None:
        _validate_engine_version(engine_version)
        self._repository = repository
        self._engine_version = engine_version

    def get(self, key: str) -> tuple[str, PanchangResult] | None:
        record = self._repository.get(key)
        if record is None:
            return None
        engine_version, payload = record
        if engine_version != self._engine_version:
            return None
        return engine_version, PanchangResult.model_validate_json(payload)

    def put(self, key: str, engine_version: str, result: PanchangResult) -> None:
        if engine_version != self._engine_version:
            raise ValueError("engine_version does not match store version")
        self._repository.put(
            key,
            engine_version,
            result.model_dump_json(),
        )


# ──────────────────────────────────────────────────────────────────────────
# Read-through cache
# ──────────────────────────────────────────────────────────────────────────

ComputeFn = Callable[[PanchangRequest], PanchangResult]


_PROCESS_LOCKS_GUARD = threading.Lock()
_PROCESS_LOCKS: WeakValueDictionary[str, threading.Lock] = WeakValueDictionary()


def _lock_for(key: str) -> threading.Lock:
    """Return a process-wide lock for *key* (the stampede lock protocol)."""
    with _PROCESS_LOCKS_GUARD:
        lock = _PROCESS_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _PROCESS_LOCKS[key] = lock
        return lock


class PanchangCache:
    """Read-through cache in front of the Panchang engine.

    Lookup order on `get`:
      1. Hot store (Redis) — return immediately on a version-matching hit.
      2. Durable store (Postgres) — on a version-matching hit, re-warm the
         hot store and return.
      3. Compute via the engine, persist to both stores, and return.

    A version mismatch at any layer is treated as a miss: the entry is
    stale (produced by a different engine version) and must be recomputed.
    """

    def __init__(
        self,
        compute: ComputeFn,
        hot_store: CacheStore | None = None,
        durable_store: PanchangDayRepository | None = None,
        ttl_seconds: int = 86_400,
        engine_version: str = ENGINE_VERSION,
        grid_degrees: float = LOCATION_GRID_DEGREES,
        key_lock: KeyLock | None = None,
    ) -> None:
        self._ttl = _validate_ttl(ttl_seconds)
        _validate_engine_version(engine_version)
        self._compute = compute
        self._hot = hot_store if hot_store is not None else InMemoryCacheStore()
        self._durable = durable_store if durable_store is not None else InMemoryPanchangDayStore()
        self._engine_version = engine_version
        self._grid = _validate_grid(grid_degrees)
        if key_lock is None and (
            isinstance(self._hot, RedisStore) or isinstance(self._durable, PostgresPanchangDayStore)
        ):
            raise ValueError("shared cache stores require an injected distributed key_lock")
        self._key_lock = key_lock or _local_key_lock

    def get(self, request: PanchangRequest) -> PanchangResult:
        identity = cache_key_for(
            request, grid_degrees=self._grid, engine_version=self._engine_version
        )
        key = identity.as_string()
        canonical = request.model_copy(update={"lat": identity.lat_grid, "lon": identity.lon_grid})

        hit = self._hot.get(key)
        if hit is not None and hit[0] == self._engine_version:
            _validate_result(hit[1], canonical)
            return hit[1]

        # Re-check both stores after taking the keyed lock.  This makes cold
        # requests from concurrent threads/tasks share one engine computation.
        with self._key_lock(key) as check_lock:
            hit = self._hot.get(key)
            if hit is not None and hit[0] == self._engine_version:
                _validate_result(hit[1], canonical)
                return hit[1]

            durable_hit = self._durable.get(key)
            if durable_hit is not None and durable_hit[0] == self._engine_version:
                _validate_result(durable_hit[1], canonical)
                self._hot.set(key, self._engine_version, durable_hit[1], self._ttl)
                return durable_hit[1]

            result = self._compute(canonical)
            _validate_result(result, canonical)
            if check_lock is not None:
                check_lock()
            self._durable.put(key, self._engine_version, result)
            if check_lock is not None:
                check_lock()
            self._hot.set(key, self._engine_version, result, self._ttl)
            return result


@contextmanager
def _local_key_lock(key: str) -> Iterator[None]:
    with _lock_for(key):
        yield


def _validate_result(result: PanchangResult, request: PanchangRequest) -> None:
    validated = PanchangResult.model_validate(result.model_dump(mode="python"))
    if validated.request != request:
        raise ValueError("Panchang result identity differs from cache key")
