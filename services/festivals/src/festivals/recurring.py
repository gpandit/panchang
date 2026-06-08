"""Cyclic (recurring) observances: Ekadashi, Pradosham, Sankashti, Purnima,
Amavasya and Sankranti.

Unlike named festivals (one rule -> one date a year), these recur on a fixed
cadence tied to the Tithi or solar-rashi cycle — roughly twice a month for
Tithi-based ones, twelve times a year for Sankranti. We generate every
occurrence in the requested Gregorian year by scanning the cached Panchang
day-by-day and matching the headline anga, exactly as `resolver` does for
named festivals — astronomy is read from the cache, never recomputed here.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta
from enum import Enum

from festivals.models import FestivalOccurrence
from festivals.resolver import PanchangSource, _local_tithi_index
from panchang.models import PanchangResult


class RecurringKind(str, Enum):
    EKADASHI = "ekadashi"
    PRADOSHAM = "pradosham"
    SANKASHTI = "sankashti"
    PURNIMA = "purnima"
    AMAVASYA = "amavasya"
    SANKRANTI = "sankranti"


_NAMES = {
    RecurringKind.EKADASHI: "Ekadashi",
    RecurringKind.PRADOSHAM: "Pradosham",
    RecurringKind.SANKASHTI: "Sankashti Chaturthi",
    RecurringKind.PURNIMA: "Purnima",
    RecurringKind.AMAVASYA: "Amavasya",
    RecurringKind.SANKRANTI: "Sankranti",
}


def _year_days(year: int) -> Iterable[date]:
    d = date(year, 1, 1)
    end = date(year, 12, 31)
    while d <= end:
        yield d
        d += timedelta(days=1)


def _matches(kind: RecurringKind, result: PanchangResult) -> bool:
    cal = result.calendrical
    headline = result.tithi[0]
    local_index = _local_tithi_index(headline.index)

    if kind is RecurringKind.EKADASHI:
        return local_index == 11
    if kind is RecurringKind.PRADOSHAM:
        # Pradosh vrat is observed on Trayodashi (13th tithi of either paksha) —
        # the evening twilight of that Panchang day.
        return local_index == 13
    if kind is RecurringKind.SANKASHTI:
        # Sankashti Chaturthi: the 4th tithi of Krishna Paksha, monthly.
        return cal.paksha == "Krishna Paksha" and local_index == 4
    if kind is RecurringKind.PURNIMA:
        return headline.name == "Purnima"
    if kind is RecurringKind.AMAVASYA:
        return headline.name == "Amavasya"
    raise ValueError(f"_matches does not handle {kind!r} — Sankranti uses _generate_sankranti")


def _generate_anga_recurrence(
    kind: RecurringKind, year: int, source: PanchangSource
) -> list[FestivalOccurrence]:
    """Walk the year collecting matches, collapsing a Vriddhi tithi (matches
    on two consecutive sunrises) down to its first day — the conventional
    "udaya-vyApti" observance day."""
    occurrences: list[FestivalOccurrence] = []
    prev_global_index: int | None = None
    prev_day: date | None = None

    for day in _year_days(year):
        result = source(day)
        if not _matches(kind, result):
            prev_global_index = None
            prev_day = None
            continue

        headline = result.tithi[0]
        is_continuation = (
            prev_day is not None
            and prev_global_index == headline.index
            and day - prev_day == timedelta(days=1)
        )
        if not is_continuation:
            cal = result.calendrical
            occurrences.append(
                FestivalOccurrence(
                    rule_id=f"recurring:{kind.value}",
                    name=_NAMES[kind],
                    category="vrat",
                    date=day,
                    lunar_month=cal.lunar_month,
                    paksha=cal.paksha,
                    tithi_name=headline.name,
                    is_adhika_month=cal.is_adhika_month,
                    is_kshaya_month=cal.is_kshaya_month,
                )
            )
        prev_global_index = headline.index
        prev_day = day

    return occurrences


def _generate_sankranti(year: int, source: PanchangSource) -> list[FestivalOccurrence]:
    """One occurrence per solar-rashi transition — twelve a year."""
    occurrences: list[FestivalOccurrence] = []
    prev_rashi: str | None = None
    for day in _year_days(year):
        result = source(day)
        cal = result.calendrical
        if prev_rashi is not None and prev_rashi != cal.sun_rashi:
            occurrences.append(
                FestivalOccurrence(
                    rule_id="recurring:sankranti",
                    name=f"{cal.sun_rashi} Sankranti",
                    category="festival",
                    date=day,
                    lunar_month=cal.lunar_month,
                    paksha=cal.paksha,
                    tithi_name=result.tithi[0].name,
                    is_adhika_month=cal.is_adhika_month,
                    is_kshaya_month=cal.is_kshaya_month,
                    note=f"Sun enters {cal.sun_rashi}",
                )
            )
        prev_rashi = cal.sun_rashi
    return occurrences


def generate_year(
    kind: RecurringKind, year: int, source: PanchangSource
) -> list[FestivalOccurrence]:
    """Generate every occurrence of `kind` within the Gregorian `year`."""
    if kind is RecurringKind.SANKRANTI:
        return _generate_sankranti(year, source)
    return _generate_anga_recurrence(kind, year, source)
