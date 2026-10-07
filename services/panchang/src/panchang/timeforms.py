"""Conversions between Julian Day (UT) and the three display time-forms."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from panchang import engine
from panchang.models import TimeValue


def jd_to_local_datetime(jd_ut: float, tz: str) -> datetime:
    y, m, d, h = engine.revjul(jd_ut)
    hour = int(h)
    minute = int((h - hour) * 60)
    second = round((((h - hour) * 60) - minute) * 60)
    if second == 60:
        second = 0
        minute += 1
    if minute == 60:
        minute = 0
        hour += 1
    base = datetime(y, m, d, hour % 24, minute, second, tzinfo=ZoneInfo("UTC"))
    base += timedelta(days=hour // 24)
    return base.astimezone(ZoneInfo(tz))


def to_time_value(jd_ut: float, tz: str, day_start_local: datetime) -> TimeValue:
    """Render *jd_ut* in 12h / 24h / 24-plus forms.

    `day_start_local` is the local sunrise that anchors the Panchang day. The
    24-plus form is clock time relative to the midnight that opens the
    Panchang day's civil date: a moment past local midnight but still within
    this Panchang day (i.e. before the next sunrise) reads as 24:xx, 25:xx...
    rather than wrapping back to 00:xx.
    """
    local = jd_to_local_datetime(jd_ut, tz)

    hour_24 = local.strftime("%H:%M:%S")
    hour_12 = local.strftime("%I:%M:%S %p")

    civil_midnight = day_start_local.replace(hour=0, minute=0, second=0, microsecond=0)
    # Aware datetimes sharing an IANA tz subtract in wall time in Python, which
    # goes backwards at a fall-back fold. 24-plus display uses elapsed instants;
    # civil labels remain available separately in hour_24/hour_12/iso.
    elapsed = local.astimezone(UTC) - civil_midnight.astimezone(UTC)
    total_seconds = int(elapsed.total_seconds())
    plus_hour = total_seconds // 3600
    remainder = total_seconds % 3600
    plus_minute = remainder // 60
    plus_second = remainder % 60
    hour_24_plus = f"{plus_hour:02d}:{plus_minute:02d}:{plus_second:02d}"

    return TimeValue(
        iso=local.isoformat(),
        hour_24=hour_24,
        hour_12=hour_12,
        hour_24_plus=hour_24_plus,
    )
