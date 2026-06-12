"""Tests: panchang_client.fetch_daily_panchang — downstream HTTP contract.

test_panchang.py exercises the /v1/panchang/daily router but bypasses the
real downstream call (via cache-seeding or mocking fetch_daily_panchang
itself). These tests cover the actual HTTP request/response mapping against
the panchang service's /compute endpoint.
"""

from __future__ import annotations

from unittest.mock import patch

import httpx

from api.cache import get_panchang_cache, panchang_cache_key
from api.panchang_client import fetch_daily_panchang


def _time(t: str) -> dict[str, str]:
    return {"iso": t, "hour_24": t[:5], "hour_12": t[:5], "hour_24_plus": t[:5]}


def _anga(name: str, idx: int) -> dict[str, object]:
    return {"index": idx, "name": name, "start": None, "end": None}


# Shape of services/panchang's PanchangResult.model_dump(mode="json") for
# POST /compute — note the request fields are nested under "request".
PANCHANG_SERVICE_RESPONSE = {
    "request": {
        "date": "2025-01-14",
        "lat": 28.6139,
        "lon": 77.209,
        "tz": "Asia/Kolkata",
        "ayanamsa": "lahiri",
        "month_scheme": "amanta",
    },
    "sun_longitude": 270.0,
    "moon_longitude": 45.0,
    "ayanamsa_value": 23.8,
    "tithi": [_anga("Pratipada", 1)],
    "nakshatra": [_anga("Ashwini", 1)],
    "yoga": [_anga("Vishkambha", 1)],
    "karana": [_anga("Bava", 1)],
    "vara": _anga("Mangalvara", 3),
    "day_events": {
        "sunrise": _time("07:15"),
        "sunset": _time("17:45"),
        "moonrise": _time("08:00"),
        "moonset": _time("20:00"),
    },
    "muhurat": [{"name": "Brahma Muhurta", "start": _time("05:30"), "end": _time("06:15")}],
    "choghadiya": [
        {"name": "Udveg", "start": _time("07:15"), "end": _time("08:37"), "is_day": True}
    ],
    "hora": [{"name": "Mars", "start": _time("07:15"), "end": _time("08:15")}],
    "calendrical": {
        "shaka_samvat": 1946,
        "vikram_samvat": 2081,
        "gujarati_samvat": 2081,
        "samvatsara": "Krodhi",
        "ritu": "Shishira",
        "ayana": "Uttarayana",
        "lunar_month": "Pausha",
        "is_adhika_month": False,
        "is_kshaya_month": False,
        "paksha": "Krishna",
        "moon_rashi": "Mesha",
        "sun_rashi": "Makara",
    },
}


_RealAsyncClient = httpx.AsyncClient


def _mock_client_factory(handler):
    def factory(*, timeout=None, **kwargs):
        return _RealAsyncClient(transport=httpx.MockTransport(handler), timeout=timeout)

    return factory


async def test_fetch_daily_panchang_maps_downstream_response() -> None:
    """A cache-miss POSTs to /compute and maps the nested response into DailyPanchangOut."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/compute"
        return httpx.Response(200, json=PANCHANG_SERVICE_RESPONSE)

    with patch("api.panchang_client.httpx.AsyncClient", new=_mock_client_factory(handler)):
        result = await fetch_daily_panchang(
            date="2025-01-14", lat=28.6139, lon=77.2090, tz="Asia/Kolkata"
        )

    assert result.cached is False
    assert result.date == "2025-01-14"
    assert result.lat == 28.6139
    assert result.tz == "Asia/Kolkata"
    assert result.ayanamsa == "lahiri"
    assert result.month_scheme == "amanta"
    assert result.tithi[0].name == "Pratipada"
    assert result.calendrical.samvatsara == "Krodhi"


async def test_fetch_daily_panchang_caches_result() -> None:
    """The mapped result is stored in the LRU cache for subsequent lookups."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=PANCHANG_SERVICE_RESPONSE)

    with patch("api.panchang_client.httpx.AsyncClient", new=_mock_client_factory(handler)):
        await fetch_daily_panchang(date="2025-01-14", lat=28.6139, lon=77.2090, tz="Asia/Kolkata")

    key = panchang_cache_key("2025-01-14", 28.6139, 77.2090, "Asia/Kolkata", "lahiri", "amanta")
    _, hit = get_panchang_cache().get(key)
    assert hit is True


async def test_fetch_daily_panchang_raises_on_downstream_error() -> None:
    """A non-2xx from the panchang service surfaces as httpx.HTTPStatusError."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "boom"})

    with patch("api.panchang_client.httpx.AsyncClient", new=_mock_client_factory(handler)):
        try:
            await fetch_daily_panchang(date="2025-01-14", lat=28.6139, lon=77.2090, tz="Asia/Kolkata")
        except httpx.HTTPStatusError as exc:
            assert exc.response.status_code == 500
        else:
            raise AssertionError("expected httpx.HTTPStatusError")
