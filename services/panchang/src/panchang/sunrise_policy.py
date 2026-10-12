"""Named high-latitude approximation: nearest valid inward latitude.

All returned Julian Days are UTC instants. A reference latitude supplies a
*proxy*, never an observed event at the requested coordinates.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from math import radians, sin
from zoneinfo import ZoneInfo

from panchang import engine
from panchang.timeforms import jd_to_local_datetime

POLICY = "sunriseFallbackNearestValidLatitude"


class SunriseFallbackError(ValueError):
    """No valid local-day anchor can be obtained; no Panchang is emitted."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        self.flags = ["sunriseFallback", "sunriseFallbackUnavailable", reason]
        super().__init__(f"{POLICY}: {reason}")


def _local_midnight(day: date, tz: ZoneInfo) -> datetime:
    midnight = datetime(day.year, day.month, day.day, tzinfo=tz)
    if midnight.astimezone(UTC).astimezone(tz).replace(tzinfo=None) != midnight.replace(
        tzinfo=None
    ):
        raise SunriseFallbackError("impossibleLocalDate")
    return midnight


def _event_triplet(
    day: date, lon: float, lat: float, tz: str, midnight_jd: float
) -> tuple[float, float, float] | None:
    """Only accept a rise on day, set after it, and rise on the next local date."""
    rise = engine.sun_rise(midnight_jd, lon, lat)
    if rise is None or jd_to_local_datetime(rise, tz).date() != day:
        return None
    set_ = engine.sun_set(rise + 1e-5, lon, lat)
    if set_ is None or jd_to_local_datetime(set_, tz).date() != day:
        return None
    next_rise = engine.sun_rise(set_ + 1e-5, lon, lat)
    if next_rise is None or jd_to_local_datetime(next_rise, tz).date() != day + timedelta(days=1):
        return None
    if not midnight_jd <= rise < set_ < next_rise:
        return None
    return rise, set_, next_rise


def sunrise_interval(
    day: date, lon: float, lat: float, tz_name: str
) -> tuple[float, float, float, list[str]]:
    """Observed triplet or nearest valid latitude at same longitude/local date.

    Search inward in 1° steps, then the equator. This bounds the search at 91
    candidates and avoids carrying an event from a different calendar day.
    """
    tz = ZoneInfo(tz_name)
    try:
        next_day = day + timedelta(days=1)
        midnight = _local_midnight(day, tz)
        _local_midnight(next_day, tz)
    except (OverflowError, ValueError) as exc:
        if isinstance(exc, SunriseFallbackError):
            raise
        raise SunriseFallbackError("impossibleLocalDate") from exc

    midnight_utc = midnight.astimezone(UTC)
    midnight_jd = engine.julday(
        midnight_utc.year,
        midnight_utc.month,
        midnight_utc.day,
        midnight_utc.hour
        + midnight_utc.minute / 60
        + midnight_utc.second / 3600
        + midnight_utc.microsecond / 3_600_000_000,
    )
    observed = _event_triplet(day, lon, lat, tz_name, midnight_jd)
    if observed is not None:
        return *observed, []

    # Tropical solar longitude's sign of declination identifies which pole
    # faces the Sun. This is a seasonal classification, not an observed event.
    season = (
        (
            ["polarDay"]
            if sin(radians(engine.get_planet_longitude(midnight_jd))) * lat > 0
            else ["polarNight"]
        )
        if abs(lat) >= 66
        else []
    )
    for step in range(1, 91):
        candidate = max(0.0, abs(lat) - step)
        proxy = _event_triplet(
            day, lon, candidate if lat >= 0 else -candidate, tz_name, midnight_jd
        )
        if proxy is not None:
            return *proxy, ["sunriseFallback", POLICY, *season]
        if candidate == 0.0:
            break
    if candidate != 0.0:
        proxy = _event_triplet(day, lon, 0.0, tz_name, midnight_jd)
        if proxy is not None:
            return *proxy, ["sunriseFallback", POLICY, *season]
    raise SunriseFallbackError("noValidLatitude")
