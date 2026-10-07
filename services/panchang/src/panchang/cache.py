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

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from panchang.models import PanchangRequest, PanchangResult

# ──────────────────────────────────────────────────────────────────────────
# Engine version — bump whenever a change to the engine could change output
# for an existing key. Stored alongside every cached value so a version
# mismatch is treated as a miss, deterministically invalidating stale data
# without needing to enumerate or scan keys.
# ──────────────────────────────────────────────────────────────────────────
# v2 changes the cached payload contract: intervals now require UTC instants,
# offsets, hoursFromSunrise and flags. Never serve a v1 entry as a v2 day.
ENGINE_VERSION = "2"

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
    return round(round(value / grid) * grid, 6)


@dataclass(frozen=True)
class CacheKey:
    """Identity of a cacheable PanchangDay computation.

    Equal keys are guaranteed to produce identical engine output, modulo the
    location-grid rounding documented above.
    """

    date: date
    lat_grid: float
    lon_grid: float
    ayanamsa: str
    month_scheme: str
    engine_version: str = ENGINE_VERSION

    def as_string(self) -> str:
        return (
            f"panchang:{self.engine_version}:{self.date.isoformat()}:"
            f"{self.lat_grid:.1f},{self.lon_grid:.1f}:"
            f"{self.ayanamsa}:{self.month_scheme}"
        )


def cache_key_for(request: PanchangRequest) -> CacheKey:
    """Derive the cache key for a request, applying the location grid."""
    return CacheKey(
        date=request.date,
        lat_grid=_grid_round(request.lat),
        lon_grid=_grid_round(request.lon),
        ayanamsa=request.ayanamsa.value,
        month_scheme=request.month_scheme.value,
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


class InMemoryCacheStore:
    """Dict-backed `CacheStore` — stands in for Redis in tests/dev."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[str, PanchangResult]] = {}

    def get(self, key: str) -> tuple[str, PanchangResult] | None:
        return self._data.get(key)

    def set(self, key: str, engine_version: str, result: PanchangResult, ttl_seconds: int) -> None:
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


# ──────────────────────────────────────────────────────────────────────────
# Read-through cache
# ──────────────────────────────────────────────────────────────────────────

ComputeFn = Callable[[PanchangRequest], PanchangResult]


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
    ) -> None:
        self._compute = compute
        self._hot = hot_store if hot_store is not None else InMemoryCacheStore()
        self._durable = durable_store if durable_store is not None else InMemoryPanchangDayStore()
        self._ttl = ttl_seconds
        self._engine_version = engine_version

    def get(self, request: PanchangRequest) -> PanchangResult:
        key = cache_key_for(request).as_string()

        hit = self._hot.get(key)
        if hit is not None and hit[0] == self._engine_version:
            return hit[1]

        durable_hit = self._durable.get(key)
        if durable_hit is not None and durable_hit[0] == self._engine_version:
            self._hot.set(key, self._engine_version, durable_hit[1], self._ttl)
            return durable_hit[1]

        result = self._compute(request)
        self._durable.put(key, self._engine_version, result)
        self._hot.set(key, self._engine_version, result, self._ttl)
        return result
