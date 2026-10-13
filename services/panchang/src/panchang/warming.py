"""Cache-warming job (Step 1.4).

Precomputes a rolling horizon of PanchangDay results for a configured set of
"popular" locations, so the common-case read path always hits a warm cache.

In production this runs as a scheduled job on the Redis-backed queue (RQ/Arq),
re-enqueued daily so the horizon keeps rolling forward. The function here is
the unit of work that job invokes; it is queue-agnostic so it can be tested
and run synchronously.
"""

from __future__ import annotations

import calendar
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

from panchang.cache import PanchangCache
from panchang.models import Ayanamsa, MonthScheme, PanchangRequest

# Default rolling horizon in actual calendar months.
DEFAULT_HORIZON_MONTHS = 15
# Retained as a named compatibility value for callers that explicitly choose
# the old approximate day horizon.  The default warmer uses calendar months.
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
    horizon_days: int | None = None,
    locations: list[PopularLocation] | None = None,
    ayanamsa: Ayanamsa = Ayanamsa.LAHIRI,
    month_scheme: MonthScheme = MonthScheme.AMANTA,
    horizon_months: int = DEFAULT_HORIZON_MONTHS,
    month_schemes: Iterable[MonthScheme] | None = None,
) -> int:
    """Populate *cache* for every (day, location, scheme) pair in the horizon.

    By default the horizon is fifteen actual calendar months from ``start``.
    ``horizon_days`` remains an explicit override for legacy/manual jobs, and
    ``month_schemes`` can request both supported lunar-month schemes.

    Returns the number of pairs warmed. Each `cache.get`
    call is itself the read-through compute-and-store operation — calling
    it here simply ensures the entry exists ahead of any user request.
    """
    if (
        isinstance(horizon_months, bool)
        or not isinstance(horizon_months, int)
        or horizon_months <= 0
    ):
        raise ValueError("horizon_months must be a positive integer")
    if horizon_days is not None and (
        isinstance(horizon_days, bool) or not isinstance(horizon_days, int) or horizon_days <= 0
    ):
        raise ValueError("horizon_days must be a positive integer")

    locations = locations if locations is not None else DEFAULT_POPULAR_LOCATIONS
    if month_schemes is None:
        schemes = [month_scheme]
    else:
        schemes = list(month_schemes)
        if not schemes:
            raise ValueError("month_schemes must contain at least one scheme")
        schemes = list(dict.fromkeys(schemes))

    if horizon_days is None:
        horizon_end = _add_months(start, horizon_months)
        days = (horizon_end - start).days
    else:
        # Explicit day counts remain supported for small/manual warm jobs.
        days = horizon_days

    count = 0
    for offset in range(days):
        day = start + timedelta(days=offset)
        for loc in locations:
            for scheme in schemes:
                request = PanchangRequest(
                    date=day,
                    lat=loc.lat,
                    lon=loc.lon,
                    tz=loc.tz,
                    ayanamsa=ayanamsa,
                    month_scheme=scheme,
                )
                cache.get(request)
                count += 1
    return count


def _add_months(value: date, months: int) -> date:
    """Return *value* advanced by calendar months, clamping month-end days."""
    month_index = value.year * 12 + value.month - 1 + months
    year, month_zero_based = divmod(month_index, 12)
    month = month_zero_based + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)
