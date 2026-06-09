"""In-process LRU cache for read-heavy, location-keyed Panchang data.

This layer sits in front of the downstream panchang service and is the
primary latency lever for the < 2 s daily-Panchang budget.

In production this would be backed by Redis; the interface is the same so
swapping the backend is a one-file change. For local dev and tests, the
in-memory LRU is sufficient (no Redis dependency required).

Edge / CDN caching is complementary — the routers emit correct
Cache-Control / Surrogate-Key headers so Cloudflare / Fastly can cache
at the PoP level as well.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any

from api.settings import get_settings


class LRUCache:
    """Thread-safe (GIL-protected) LRU cache with per-entry TTL."""

    def __init__(self, max_size: int, default_ttl: int) -> None:
        self._max_size = max_size
        self._default_ttl = default_ttl
        # OrderedDict maintains insertion/access order (LRU eviction)
        self._store: OrderedDict[str, tuple[Any, float]] = OrderedDict()

    def get(self, key: str) -> tuple[Any, bool]:
        """Return (value, hit).  Evicts the entry if expired."""
        if key not in self._store:
            return None, False
        value, expires_at = self._store[key]
        if time.monotonic() > expires_at:
            del self._store[key]
            return None, False
        # Move to end (most-recently-used)
        self._store.move_to_end(key)
        return value, True

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        ttl = ttl if ttl is not None else self._default_ttl
        expires_at = time.monotonic() + ttl
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = (value, expires_at)
        if len(self._store) > self._max_size:
            # Evict least-recently-used (first item)
            self._store.popitem(last=False)

    def clear(self) -> None:
        self._store.clear()


_panchang_cache: LRUCache | None = None


def get_panchang_cache() -> LRUCache:
    global _panchang_cache
    if _panchang_cache is None:
        s = get_settings()
        _panchang_cache = LRUCache(
            max_size=s.panchang_cache_max_size,
            default_ttl=s.panchang_cache_ttl_seconds,
        )
    return _panchang_cache


def panchang_cache_key(
    date: str, lat: float, lon: float, tz: str, ayanamsa: str, month_scheme: str
) -> str:
    # Round lat/lon to 4 decimal places (~11 m grid) for cache key stability
    return f"panchang:{date}:{lat:.4f}:{lon:.4f}:{tz}:{ayanamsa}:{month_scheme}"
