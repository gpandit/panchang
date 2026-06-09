"""Recurrence resolver — turns a RecurrenceSpec into concrete fire-times.

Reads the cached Panchang day-by-day (never recomputes astronomy directly).
All lunar correctness (Vriddhi / Adhika / Kshaya) is handled by the same
logic used in `festivals.recurring` — first-sunrise for a Vriddhi Tithi,
Adhika-aware filtering for month constraints.

Every resolved occurrence carries an idempotency key
  "{reminder_id}:{occurrence_date}"
so the scheduler and delivery layer can guarantee at-most-once fires.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from api.reminders.schemas import OccurrenceRead, RecurrenceKind, RecurrenceSpec
from panchang.models import MonthScheme, PanchangRequest, PanchangResult

# Bound panchang source: given a date returns the PanchangResult for a fixed
# (lat, lon, tz, month_scheme). Matches the pattern in festivals.resolver.
PanchangSource = Callable[[date], PanchangResult]


def _local_tithi_index(global_index: int) -> int:
    """1-based index within the current paksha (1..15) from the global 1..30 index."""
    return ((global_index - 1) % 15) + 1


def _date_range(start: date, end: date) -> Iterable[date]:
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def _fire_time_utc(
    d: date,
    spec: RecurrenceSpec,
    result: PanchangResult,
    user_tz: ZoneInfo,
) -> datetime:
    """Return the UTC fire-time for occurrence on day `d`.

    If fire_at_sunrise, parse the sunrise ISO string from the PanchangResult.
    Otherwise, construct a naive local datetime from fire_hour/minute and
    convert to UTC via the user's timezone.
    """
    if spec.fire_at_sunrise and result.day_events.sunrise:
        # Sunrise is already expressed as an ISO-8601 string with offset —
        # parse it and convert to UTC.
        iso = result.day_events.sunrise.iso
        try:
            dt = datetime.fromisoformat(iso)
            return dt.astimezone(UTC)
        except ValueError:
            pass  # fall through to explicit hour/minute

    local_dt = datetime(d.year, d.month, d.day, spec.fire_hour, spec.fire_minute, tzinfo=user_tz)
    return local_dt.astimezone(UTC)


def _resolve_tithi(
    reminder_id: str,
    spec: RecurrenceSpec,
    start: date,
    end: date,
    source: PanchangSource,
    user_tz: ZoneInfo,
) -> list[OccurrenceRead]:
    """Resolve TITHI recurrences across [start, end].

    Vriddhi handling: a Tithi that spans two consecutive sunrises appears on
    both days with the same global tithi index. We take the first day only
    (udaya-vyApti convention), matching `festivals.recurring._generate_anga_recurrence`.

    Adhika handling: if lunar_month is set and observe_in_adhika=False we skip
    Adhika occurrences of that month; if observe_in_adhika=True we skip regular.
    Without lunar_month the filter does not apply.
    """
    occurrences: list[OccurrenceRead] = []
    prev_global_index: int | None = None
    prev_day: date | None = None

    for d in _date_range(start, end):
        result = source(d)
        cal = result.calendrical
        headline = result.tithi[0]
        local_idx = _local_tithi_index(headline.index)

        # tithi_index match (required)
        if spec.tithi_index is not None and local_idx != spec.tithi_index:
            prev_global_index = None
            prev_day = None
            continue

        # paksha filter (optional — None means both)
        if spec.paksha is not None and cal.paksha != spec.paksha:
            prev_global_index = None
            prev_day = None
            continue

        # lunar_month filter (optional)
        if spec.lunar_month is not None and cal.lunar_month != spec.lunar_month:
            prev_global_index = None
            prev_day = None
            continue

        # Adhika filter
        if spec.lunar_month is not None:
            if cal.is_adhika_month != spec.observe_in_adhika:
                prev_global_index = None
                prev_day = None
                continue

        # Vriddhi collapse — skip second day if global index unchanged from yesterday
        is_continuation = (
            prev_day is not None
            and prev_global_index == headline.index
            and d - prev_day == timedelta(days=1)
        )
        prev_global_index = headline.index
        prev_day = d

        if is_continuation:
            continue

        occurrence_date = d.isoformat()
        occurrences.append(
            OccurrenceRead(
                reminder_id=reminder_id,  # type: ignore[arg-type]
                occurrence_date=occurrence_date,
                fire_at=_fire_time_utc(d, spec, result, user_tz),
                idempotency_key=f"{reminder_id}:{occurrence_date}",
            )
        )

    return occurrences


def _resolve_nakshatra(
    reminder_id: str,
    spec: RecurrenceSpec,
    start: date,
    end: date,
    source: PanchangSource,
    user_tz: ZoneInfo,
) -> list[OccurrenceRead]:
    """Resolve NAKSHATRA recurrences across [start, end]."""
    occurrences: list[OccurrenceRead] = []

    for d in _date_range(start, end):
        result = source(d)
        if not result.nakshatra:
            continue
        if result.nakshatra[0].name != spec.nakshatra_name:
            continue
        occurrence_date = d.isoformat()
        occurrences.append(
            OccurrenceRead(
                reminder_id=reminder_id,  # type: ignore[arg-type]
                occurrence_date=occurrence_date,
                fire_at=_fire_time_utc(d, spec, result, user_tz),
                idempotency_key=f"{reminder_id}:{occurrence_date}",
            )
        )

    return occurrences


def _resolve_gregorian(
    reminder_id: str,
    spec: RecurrenceSpec,
    start: date,
    end: date,
    source: PanchangSource,
    user_tz: ZoneInfo,
) -> list[OccurrenceRead]:
    """Resolve GREGORIAN (annual anniversary) recurrences across [start, end]."""
    occurrences: list[OccurrenceRead] = []
    years = range(start.year, end.year + 1)

    for year in years:
        try:
            d = date(year, spec.gregorian_month, spec.gregorian_day)  # type: ignore[arg-type]
        except ValueError:
            continue  # e.g. Feb 29 in a non-leap year — skip silently
        if not (start <= d <= end):
            continue
        result = source(d)
        occurrence_date = d.isoformat()
        occurrences.append(
            OccurrenceRead(
                reminder_id=reminder_id,  # type: ignore[arg-type]
                occurrence_date=occurrence_date,
                fire_at=_fire_time_utc(d, spec, result, user_tz),
                idempotency_key=f"{reminder_id}:{occurrence_date}",
            )
        )

    return occurrences


def _resolve_weekday(
    reminder_id: str,
    spec: RecurrenceSpec,
    start: date,
    end: date,
    source: PanchangSource,
    user_tz: ZoneInfo,
) -> list[OccurrenceRead]:
    """Resolve WEEKDAY (e.g. every Monday) recurrences across [start, end]."""
    occurrences: list[OccurrenceRead] = []

    for d in _date_range(start, end):
        if d.weekday() != spec.weekday:
            continue
        result = source(d)
        occurrence_date = d.isoformat()
        occurrences.append(
            OccurrenceRead(
                reminder_id=reminder_id,  # type: ignore[arg-type]
                occurrence_date=occurrence_date,
                fire_at=_fire_time_utc(d, spec, result, user_tz),
                idempotency_key=f"{reminder_id}:{occurrence_date}",
            )
        )

    return occurrences


def make_panchang_source(
    cache_get: Callable[[PanchangRequest], PanchangResult],
    *,
    lat: float,
    lon: float,
    tz: str,
    month_scheme: MonthScheme,
) -> PanchangSource:
    """Bind a PanchangCache.get call to one (location, scheme) pair."""

    def _source(d: date) -> PanchangResult:
        return cache_get(
            PanchangRequest(date=d, lat=lat, lon=lon, tz=tz, month_scheme=month_scheme)
        )

    return _source


def resolve(
    reminder_id: str,
    spec: RecurrenceSpec,
    start: date,
    end: date,
    source: PanchangSource,
    user_tz: ZoneInfo,
) -> list[OccurrenceRead]:
    """Resolve `spec` into concrete fire-times across [start, end].

    Returns occurrences in chronological order. The caller is responsible for
    filtering out already-delivered occurrences (by idempotency_key) before
    enqueuing.
    """
    if spec.kind is RecurrenceKind.TITHI:
        return _resolve_tithi(reminder_id, spec, start, end, source, user_tz)
    if spec.kind is RecurrenceKind.NAKSHATRA:
        return _resolve_nakshatra(reminder_id, spec, start, end, source, user_tz)
    if spec.kind is RecurrenceKind.GREGORIAN:
        return _resolve_gregorian(reminder_id, spec, start, end, source, user_tz)
    if spec.kind is RecurrenceKind.WEEKDAY:
        return _resolve_weekday(reminder_id, spec, start, end, source, user_tz)
    raise ValueError(f"Unhandled RecurrenceKind: {spec.kind!r}")
