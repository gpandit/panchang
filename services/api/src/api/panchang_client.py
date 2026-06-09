"""HTTP client for the downstream Panchang computation service.

The gateway never computes Panchang itself — it always reads from this service.
Results are cached in the in-process LRU cache (and edge cache via headers)
so the < 2 s latency budget is met on cache hits without any downstream call.
"""

from __future__ import annotations

import httpx

from api.cache import get_panchang_cache, panchang_cache_key
from api.models.panchang import DailyPanchangOut
from api.settings import get_settings


async def fetch_daily_panchang(
    date: str,
    lat: float,
    lon: float,
    tz: str,
    ayanamsa: str = "lahiri",
    month_scheme: str = "amanta",
) -> DailyPanchangOut:
    """Return the daily Panchang, serving from cache when available.

    Cache hit:  returns in < 1 ms (in-process LRU).
    Cache miss: calls the downstream service (budget: < 1.5 s), caches result.
    """
    cache = get_panchang_cache()
    key = panchang_cache_key(date, lat, lon, tz, ayanamsa, month_scheme)

    cached_value, hit = cache.get(key)
    if hit:
        result = DailyPanchangOut.model_validate(cached_value)
        result.cached = True
        return result

    settings = get_settings()
    url = f"{settings.panchang_service_url}/panchang/compute"
    params = {
        "date": date,
        "lat": lat,
        "lon": lon,
        "tz": tz,
        "ayanamsa": ayanamsa,
        "month_scheme": month_scheme,
    }
    async with httpx.AsyncClient(timeout=settings.panchang_service_timeout) as client:
        resp = client.get(url, params=params) if False else await client.get(url, params=params)
        resp.raise_for_status()
        payload = resp.json()

    result = DailyPanchangOut.model_validate(payload)
    result.cached = False
    # Store the dict so it's JSON-serialisable in the cache
    cache.set(key, result.model_dump())
    return result
