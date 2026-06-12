"""Tests: daily Panchang endpoint — auth, caching, and latency budget."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from api.cache import get_panchang_cache, panchang_cache_key
from api.models.panchang import (
    AngaSpanOut,
    CalendricalOut,
    ChoghadiyaOut,
    DailyPanchangOut,
    DayEventsOut,
    PeriodOut,
    TimeValueOut,
)

# ── Fixture: a minimal but valid DailyPanchangOut ─────────────────────────────


def _time(t: str) -> TimeValueOut:
    return TimeValueOut(iso=t, hour_24=t[:5], hour_12=t[:5], hour_24_plus=t[:5])


def _anga(name: str, idx: int) -> AngaSpanOut:
    return AngaSpanOut(index=idx, name=name, start=None, end=None)


SAMPLE_PANCHANG = DailyPanchangOut(
    date="2025-01-14",
    lat=28.6139,
    lon=77.2090,
    tz="Asia/Kolkata",
    ayanamsa="lahiri",
    month_scheme="amanta",
    sun_longitude=270.0,
    moon_longitude=45.0,
    ayanamsa_value=23.8,
    tithi=[_anga("Pratipada", 1)],
    nakshatra=[_anga("Ashwini", 1)],
    yoga=[_anga("Vishkambha", 1)],
    karana=[_anga("Bava", 1)],
    vara=_anga("Mangalvara", 3),
    day_events=DayEventsOut(
        sunrise=_time("07:15"),
        sunset=_time("17:45"),
        moonrise=_time("08:00"),
        moonset=_time("20:00"),
    ),
    muhurat=[PeriodOut(name="Brahma Muhurta", start=_time("05:30"), end=_time("06:15"))],
    choghadiya=[ChoghadiyaOut(name="Udveg", start=_time("07:15"), end=_time("08:37"), is_day=True)],
    hora=[PeriodOut(name="Mars", start=_time("07:15"), end=_time("08:15"))],
    calendrical=CalendricalOut(
        shaka_samvat=1946,
        vikram_samvat=2081,
        gujarati_samvat=2081,
        samvatsara="Krodhi",
        ritu="Shishira",
        ayana="Uttarayana",
        lunar_month="Pausha",
        is_adhika_month=False,
        is_kshaya_month=False,
        paksha="Krishna",
        moon_rashi="Mesha",
        sun_rashi="Makara",
    ),
    cached=False,
)

DAILY_URL = "/v1/panchang/daily?date=2025-01-14&lat=28.6139&lon=77.2090&tz=Asia/Kolkata"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _seed_cache() -> None:
    """Pre-populate the in-process cache so tests bypass the HTTP call."""
    cache = get_panchang_cache()
    key = panchang_cache_key("2025-01-14", 28.6139, 77.2090, "Asia/Kolkata", "lahiri", "amanta")
    cache.set(key, SAMPLE_PANCHANG.model_dump())


# ── Tests ─────────────────────────────────────────────────────────────────────


async def test_daily_accessible_without_auth(client: AsyncClient) -> None:
    """The daily Panchang is the public landing view — no login required."""
    _seed_cache()
    r = await client.get(DAILY_URL)
    assert r.status_code == 200
    assert r.json()["data"]["date"] == "2025-01-14"


async def test_daily_cache_hit_returns_200(client: AsyncClient, basic_token: str) -> None:
    _seed_cache()
    r = await client.get(DAILY_URL, headers={"Authorization": f"Bearer {basic_token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["date"] == "2025-01-14"
    assert r.headers.get("X-Cache") == "HIT"


async def test_daily_cache_hit_latency_under_2s(client: AsyncClient, basic_token: str) -> None:
    """Cache hit must return well under the 2 s latency budget."""
    _seed_cache()
    start = time.perf_counter()
    r = await client.get(DAILY_URL, headers={"Authorization": f"Bearer {basic_token}"})
    elapsed = time.perf_counter() - start

    assert r.status_code == 200
    assert elapsed < 2.0, f"Cache hit took {elapsed:.3f}s — exceeds 2 s budget"


async def test_daily_cache_miss_calls_downstream(client: AsyncClient, basic_token: str) -> None:
    """On a cache miss, the gateway fetches from the downstream service."""
    with patch(
        "api.routers.v1.panchang.fetch_daily_panchang",
        new_callable=AsyncMock,
        return_value=SAMPLE_PANCHANG,
    ) as mock_fetch:
        r = await client.get(DAILY_URL, headers={"Authorization": f"Bearer {basic_token}"})

    assert r.status_code == 200
    mock_fetch.assert_awaited_once()


async def test_daily_cache_miss_latency_mock_under_2s(
    client: AsyncClient, basic_token: str
) -> None:
    """Even a mocked downstream call (0 ms) stays under the budget."""
    with patch(
        "api.routers.v1.panchang.fetch_daily_panchang",
        new_callable=AsyncMock,
        return_value=SAMPLE_PANCHANG,
    ):
        start = time.perf_counter()
        r = await client.get(DAILY_URL, headers={"Authorization": f"Bearer {basic_token}"})
        elapsed = time.perf_counter() - start

    assert r.status_code == 200
    assert elapsed < 2.0


async def test_daily_sets_cache_control_header(client: AsyncClient, basic_token: str) -> None:
    _seed_cache()
    r = await client.get(DAILY_URL, headers={"Authorization": f"Bearer {basic_token}"})
    cc = r.headers.get("cache-control", "")
    assert "max-age=3600" in cc
    assert "s-maxage=3600" in cc


async def test_daily_response_envelope(client: AsyncClient, basic_token: str) -> None:
    """Response is wrapped in the standard ApiResponse envelope."""
    _seed_cache()
    r = await client.get(DAILY_URL, headers={"Authorization": f"Bearer {basic_token}"})
    body = r.json()
    assert "data" in body
    assert "elements" in body["data"]
    assert "muhurats" in body["data"]
    assert "summaryTitle" in body["data"]
    assert "panchangHindiDate" in body["data"]


async def test_cache_warmed_on_first_hit(client: AsyncClient, basic_token: str) -> None:
    """After the cache is populated, the second request is served from cache (X-Cache: HIT)."""
    _seed_cache()
    headers = {"Authorization": f"Bearer {basic_token}"}

    r1 = await client.get(DAILY_URL, headers=headers)
    assert r1.status_code == 200
    assert r1.headers.get("X-Cache") == "HIT"

    r2 = await client.get(DAILY_URL, headers=headers)
    assert r2.status_code == 200
    assert r2.headers.get("X-Cache") == "HIT"
