"""Tests for the compute-and-cache layer (Step 1.4)."""

from datetime import date, timedelta

import pytest

from panchang.cache import (
    ENGINE_VERSION,
    InMemoryCacheStore,
    InMemoryPanchangDayStore,
    PanchangCache,
    cache_key_for,
)
from panchang.compute import compute_panchang
from panchang.models import PanchangRequest
from panchang.warming import DEFAULT_POPULAR_LOCATIONS, warm_horizon

DELHI = {"lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata"}


def _request(d: date, **overrides) -> PanchangRequest:
    return PanchangRequest(date=d, **{**DELHI, **overrides})


def _counting_compute():
    calls = []

    def compute(request: PanchangRequest):
        calls.append(request)
        return compute_panchang(request)

    return compute, calls


# ──────────────────────────────────────────────────────────────────────────
# Read-through behaviour
# ──────────────────────────────────────────────────────────────────────────


def test_repeated_request_served_from_cache_no_recompute() -> None:
    compute, calls = _counting_compute()
    cache = PanchangCache(compute)

    req = _request(date(2024, 1, 15))
    first = cache.get(req)
    second = cache.get(req)

    assert len(calls) == 1
    assert second == first


def test_cold_request_self_populates_then_hits() -> None:
    compute, calls = _counting_compute()
    hot = InMemoryCacheStore()
    durable = InMemoryPanchangDayStore()
    cache = PanchangCache(compute, hot_store=hot, durable_store=durable)

    req = _request(date(2024, 2, 1))
    key = cache_key_for(req).as_string()

    assert hot.get(key) is None
    assert durable.get(key) is None

    result = cache.get(req)
    assert hot.get(key) is not None
    assert durable.get(key) is not None
    assert len(calls) == 1

    assert cache.get(req) == result
    assert len(calls) == 1


def test_durable_hit_rewarms_hot_store_without_recompute() -> None:
    compute, calls = _counting_compute()
    hot = InMemoryCacheStore()
    durable = InMemoryPanchangDayStore()
    cache = PanchangCache(compute, hot_store=hot, durable_store=durable)

    req = _request(date(2024, 3, 10))
    key = cache_key_for(req).as_string()

    # Pre-seed only the durable store, simulating a hot-cache eviction.
    expected = compute_panchang(req)
    durable.put(key, ENGINE_VERSION, expected)
    calls.clear()

    result = cache.get(req)
    assert result == expected
    assert hot.get(key) is not None
    assert len(calls) == 0  # served from durable store, not recomputed


def test_version_mismatch_forces_recompute() -> None:
    compute, calls = _counting_compute()
    hot = InMemoryCacheStore()
    durable = InMemoryPanchangDayStore()
    cache = PanchangCache(compute, hot_store=hot, durable_store=durable)

    req = _request(date(2024, 4, 5))
    key = cache_key_for(req).as_string()

    stale = compute_panchang(req)
    hot.set(key, "stale-version", stale, ttl_seconds=86_400)
    durable.put(key, "stale-version", stale)

    cache.get(req)
    assert len(calls) == 1  # treated as a miss, recomputed and re-stored

    _, _stored_version = hot.get(key)[0], hot.get(key)[0]
    assert hot.get(key)[0] == ENGINE_VERSION
    assert durable.get(key)[0] == ENGINE_VERSION


# ──────────────────────────────────────────────────────────────────────────
# Cache-equals-compute property
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "d, lat, lon, tz",
    [
        (date(2024, 1, 15), 28.6139, 77.2090, "Asia/Kolkata"),
        (date(2024, 6, 21), 19.0760, 72.8777, "Asia/Kolkata"),
        (date(2024, 12, 25), 25.3176, 82.9739, "Asia/Kolkata"),
        (date(2025, 3, 1), 13.0827, 80.2707, "Asia/Kolkata"),
    ],
)
def test_cached_value_equals_fresh_compute(d, lat, lon, tz) -> None:
    cache = PanchangCache(compute_panchang)
    req = PanchangRequest(date=d, lat=lat, lon=lon, tz=tz)

    cached = cache.get(req)
    fresh = compute_panchang(req)

    assert cached == fresh


# ──────────────────────────────────────────────────────────────────────────
# Cache key / location grid
# ──────────────────────────────────────────────────────────────────────────


def test_nearby_locations_share_a_cache_key() -> None:
    a = _request(date(2024, 1, 15), lat=28.6139, lon=77.2090)
    b = _request(date(2024, 1, 15), lat=28.6151, lon=77.2101)  # ~150 m away

    assert cache_key_for(a).as_string() == cache_key_for(b).as_string()


def test_distant_locations_have_different_cache_keys() -> None:
    delhi = _request(date(2024, 1, 15), lat=28.6139, lon=77.2090)
    mumbai = _request(date(2024, 1, 15), lat=19.0760, lon=72.8777)

    assert cache_key_for(delhi).as_string() != cache_key_for(mumbai).as_string()


# ──────────────────────────────────────────────────────────────────────────
# Warming job
# ──────────────────────────────────────────────────────────────────────────


def test_warming_job_populates_horizon_for_popular_locations() -> None:
    compute, calls = _counting_compute()
    hot = InMemoryCacheStore()
    durable = InMemoryPanchangDayStore()
    cache = PanchangCache(compute, hot_store=hot, durable_store=durable)

    start = date(2024, 1, 1)
    horizon_days = 5
    locations = DEFAULT_POPULAR_LOCATIONS[:2]

    warmed = warm_horizon(cache, start=start, horizon_days=horizon_days, locations=locations)

    assert warmed == horizon_days * len(locations)
    assert len(calls) == horizon_days * len(locations)

    # Every (day, location) pair is now a warm hit — no further computes.
    calls.clear()
    for offset in range(horizon_days):
        d = start + timedelta(days=offset)
        for loc in locations:
            req = PanchangRequest(date=d, lat=loc.lat, lon=loc.lon, tz=loc.tz)
            cache.get(req)
    assert len(calls) == 0
