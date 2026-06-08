"""Cache-warming job (Step 1.4).

Precomputes a rolling horizon of PanchangDay results for a configured set of
"popular" locations, so the common-case read path always hits a warm cache.

In production this runs as a scheduled job on the Redis-backed queue (RQ/Arq),
re-enqueued daily so the horizon keeps rolling forward. The function here is
the unit of work that job invokes; it is queue-agnostic so it can be tested
and run synchronously.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from panchang.cache import PanchangCache
from panchang.models import Ayanamsa, MonthScheme, PanchangRequest

# Default rolling horizon, in months (~ 30-day months for scheduling purposes).
DEFAULT_HORIZON_MONTHS = 15
DEFAULT_HORIZON_DAYS = DEFAULT_HORIZON_MONTHS * 30


@dataclass(frozen=True)
class PopularLocation:
    """A location worth pre-warming, e.g. a major city."""

    name: str
    lat: float
    lon: float
    tz: str


# Configurable seed set — extend/replace via `warm_horizon(locations=...)`.
# These are illustrative "popular" cities; the real set should be driven by
# observed traffic (e.g. top-N locations by request volume).
DEFAULT_POPULAR_LOCATIONS: list[PopularLocation] = [
    PopularLocation("New Delhi", 28.6139, 77.2090, "Asia/Kolkata"),
    PopularLocation("Mumbai", 19.0760, 72.8777, "Asia/Kolkata"),
    PopularLocation("Varanasi", 25.3176, 82.9739, "Asia/Kolkata"),
]


def warm_horizon(
    cache: PanchangCache,
    *,
    start: date,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
    locations: list[PopularLocation] | None = None,
    ayanamsa: Ayanamsa = Ayanamsa.LAHIRI,
    month_scheme: MonthScheme = MonthScheme.AMANTA,
) -> int:
    """Populate *cache* for every (day, location) pair in the horizon.

    Returns the number of (day, location) pairs warmed. Each `cache.get`
    call is itself the read-through compute-and-store operation — calling
    it here simply ensures the entry exists ahead of any user request.
    """
    locations = locations if locations is not None else DEFAULT_POPULAR_LOCATIONS
    count = 0
    for offset in range(horizon_days):
        day = start + timedelta(days=offset)
        for loc in locations:
            request = PanchangRequest(
                date=day,
                lat=loc.lat,
                lon=loc.lon,
                tz=loc.tz,
                ayanamsa=ayanamsa,
                month_scheme=month_scheme,
            )
            cache.get(request)
            count += 1
    return count
