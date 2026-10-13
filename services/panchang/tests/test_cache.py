"""Tests for the compute-and-cache layer (Step 1.4)."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from time import sleep

import pytest

from panchang.cache import (
    ENGINE_VERSION,
    InMemoryCacheStore,
    InMemoryPanchangDayStore,
    PanchangCache,
    PostgresPanchangDayStore,
    RedisKeyLock,
    RedisStore,
    cache_key_for,
)
from panchang.compute import compute_panchang
from panchang.models import MonthScheme, PanchangRequest
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
    identity = cache_key_for(req)
    expected = compute_panchang(
        req.model_copy(update={"lat": identity.lat_grid, "lon": identity.lon_grid})
    )
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

    _ = hot.get(key)[0], hot.get(key)[0]
    assert hot.get(key)[0] == ENGINE_VERSION
    assert durable.get(key)[0] == ENGINE_VERSION


def test_concurrent_cold_requests_compute_once() -> None:
    req = _request(date(2024, 4, 6))
    identity = cache_key_for(req)
    expected = compute_panchang(
        req.model_copy(update={"lat": identity.lat_grid, "lon": identity.lon_grid})
    )
    calls = 0

    def compute(_request: PanchangRequest):
        nonlocal calls
        calls += 1
        sleep(0.02)
        return expected

    cache = PanchangCache(compute)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: cache.get(req), range(8)))

    assert calls == 1
    assert all(result == expected for result in results)


@pytest.mark.parametrize("ttl", [0, -1, True, 1.5])
def test_cache_rejects_invalid_ttl(ttl) -> None:
    with pytest.raises(ValueError, match="ttl_seconds"):
        PanchangCache(compute_panchang, ttl_seconds=ttl)


class _RedisFake:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.ttl: dict[str, int] = {}

    def get(self, key: str):
        return self.values.get(key)

    def set(self, key: str, value: str, *, ex: int):
        self.values[key] = value
        self.ttl[key] = ex


def test_redis_store_round_trips_serialized_result_and_ttl() -> None:
    req = _request(date(2024, 5, 1))
    result = compute_panchang(req)
    client = _RedisFake()
    store = RedisStore(client)

    store.set("key", ENGINE_VERSION, result, 123)
    hit = store.get("key")

    assert hit == (ENGINE_VERSION, result)
    assert client.ttl["key"] == 123


def test_postgres_store_rejects_stale_engine_version() -> None:
    class Repository:
        def __init__(self) -> None:
            self.rows = {}

        def get(self, key):
            return self.rows.get(key)

        def put(self, key, engine_version, payload):
            self.rows[key] = (engine_version, payload)

    req = _request(date(2024, 5, 2))
    result = compute_panchang(req)
    repository = Repository()
    store = PostgresPanchangDayStore(repository)
    store.put("key", ENGINE_VERSION, result)
    assert store.get("key") == (ENGINE_VERSION, result)

    repository.rows["key"] = ("old-engine", repository.rows["key"][1])
    assert store.get("key") is None


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
    identity = cache_key_for(req)
    fresh = compute_panchang(
        req.model_copy(update={"lat": identity.lat_grid, "lon": identity.lon_grid})
    )

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


def test_identity_separates_timezone_scheme_grid_and_engine_version() -> None:
    request = _request(date(2024, 1, 15))
    base = cache_key_for(request).as_string()
    assert base != cache_key_for(request.model_copy(update={"tz": "Europe/London"})).as_string()
    assert (
        base
        != cache_key_for(
            request.model_copy(update={"month_scheme": MonthScheme.PURNIMANTA})
        ).as_string()
    )
    assert base != cache_key_for(request, grid_degrees=0.01).as_string()
    assert base != cache_key_for(request, engine_version="4").as_string()
    assert cache_key_for(request.model_copy(update={"lat": 28.65})).lat_grid == 28.7
    assert cache_key_for(request.model_copy(update={"lat": -28.65})).lat_grid == -28.7


@pytest.mark.parametrize("changes", [{"tz": "Bad/Zone"}, {"lat": float("nan")}, {"lon": 181}])
def test_invalid_request_never_computes_or_writes(changes) -> None:
    compute, calls = _counting_compute()
    cache = PanchangCache(compute)
    with pytest.raises(ValueError):
        cache.get(_request(date(2024, 1, 15)).model_copy(update=changes))
    assert not calls


def test_invalid_result_and_durable_failure_do_not_populate_hot_store() -> None:
    request = _request(date(2024, 1, 15))
    wrong = compute_panchang(_request(date(2024, 1, 16)))
    hot = InMemoryCacheStore()
    durable = InMemoryPanchangDayStore()
    with pytest.raises(ValueError, match="identity"):
        PanchangCache(lambda _: wrong, hot, durable).get(request)
    assert hot.get(cache_key_for(request).as_string()) is None
    assert durable.get(cache_key_for(request).as_string()) is None

    class FailedWrite(InMemoryPanchangDayStore):
        def put(self, *args):
            raise OSError("database unavailable")

    with pytest.raises(OSError, match="database unavailable"):
        PanchangCache(compute_panchang, hot, FailedWrite()).get(request)
    assert hot.get(cache_key_for(request).as_string()) is None


def test_two_cache_instances_share_injected_lock_and_stores() -> None:
    request = _request(date(2024, 1, 15))
    hot, durable = InMemoryCacheStore(), InMemoryPanchangDayStore()
    locks = {}
    import threading
    from contextlib import contextmanager

    @contextmanager
    def lock(key):
        locks.setdefault(key, threading.Lock())
        with locks[key]:
            yield

    calls = []

    def compute(req):
        calls.append(req)
        sleep(0.02)
        return compute_panchang(req)

    caches = [PanchangCache(compute, hot, durable, key_lock=lock) for _ in range(2)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        values = list(pool.map(lambda cache: cache.get(request), caches))
    assert values[0] == values[1]
    assert len(calls) == 1


def test_redis_lock_contention_and_expired_lease_fail_closed() -> None:
    class Lock:
        def __init__(self, acquired, owned):
            self.acquired, self.is_owned = acquired, owned
            self.released = False

        def acquire(self):
            return self.acquired

        def owned(self):
            return self.is_owned

        def release(self):
            self.released = True

    class Client:
        def __init__(self, lock):
            self.value = lock
            self.names = []

        def lock(self, name, *, timeout, blocking_timeout):
            self.names.append((name, timeout, blocking_timeout))
            return self.value

    request = _request(date(2024, 1, 15))
    denied = Client(Lock(False, False))
    with pytest.raises(TimeoutError, match="unavailable"):
        PanchangCache(compute_panchang, key_lock=RedisKeyLock(denied)).get(request)
    assert denied.names[0][0].endswith(":lock")

    expired = Client(Lock(True, False))
    durable = InMemoryPanchangDayStore()
    with pytest.raises(TimeoutError, match="expired"):
        PanchangCache(compute_panchang, durable_store=durable, key_lock=RedisKeyLock(expired)).get(
            request
        )
    assert durable.get(cache_key_for(request).as_string()) is None
    assert not expired.value.released


def test_shared_stores_require_distributed_lock() -> None:
    with pytest.raises(ValueError, match="distributed key_lock"):
        PanchangCache(compute_panchang, hot_store=RedisStore(_RedisFake()))


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


class _RecordingCache:
    def __init__(self) -> None:
        self.requests: list[PanchangRequest] = []

    def get(self, request: PanchangRequest):
        self.requests.append(request)


def test_warming_default_covers_fifteen_calendar_months() -> None:
    cache = _RecordingCache()
    location = DEFAULT_POPULAR_LOCATIONS[:1]

    count = warm_horizon(cache, start=date(2024, 1, 1), locations=location)

    assert count == 456 * len(location)  # Jan 1 2024 through Apr 1 2025.
    assert cache.requests[0].date == date(2024, 1, 1)
    assert cache.requests[-1].date == date(2025, 3, 31)


def test_warming_can_cover_both_month_schemes() -> None:
    cache = _RecordingCache()
    location = DEFAULT_POPULAR_LOCATIONS[:1]

    count = warm_horizon(
        cache,
        start=date(2024, 1, 1),
        horizon_days=2,
        locations=location,
        month_schemes=(MonthScheme.AMANTA, MonthScheme.PURNIMANTA),
    )

    assert count == 4
    assert {request.month_scheme for request in cache.requests} == {
        MonthScheme.AMANTA,
        MonthScheme.PURNIMANTA,
    }


@pytest.mark.parametrize("kwargs", [{"horizon_days": 0}, {"horizon_months": 0}])
def test_warming_rejects_invalid_horizon(kwargs) -> None:
    with pytest.raises(ValueError, match="horizon_"):
        warm_horizon(_RecordingCache(), start=date(2024, 1, 1), locations=[], **kwargs)
