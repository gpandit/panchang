"""Resolves `FestivalRule`s into concrete `FestivalOccurrence`s.

This module is the *only* place that turns a rule into a date. It never
computes astronomy itself — every Panchang value it reads comes from the
cached compute-and-cache layer (`panchang.cache.PanchangCache`), per the
architectural rule that the Panchang engine is the single source of
astronomical truth (Architecture §2 / non-negotiable #1 & #2).

Resolution scans the cached Panchang day-by-day across the requested
Gregorian year and matches each rule's condition against the *headline*
anga — the one active when the Panchang day opens at sunrise. That mirrors
how a published Panchang headlines a day's Tithi/Nakshatra, and is exactly
what `PanchangResult.tithi[0]` / `.nakshatra[0]` / `.calendrical` already
represent (see `compute.compute_panchang`).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import date, timedelta

from festivals.models import FestivalOccurrence, FestivalRule, RuleKind
from panchang.models import MonthScheme, PanchangRequest, PanchangResult

# A location-and-scheme-bound source of Panchang days. Production code binds
# this to `PanchangCache.get`; tests can bind it to anything that returns a
# deterministic `PanchangResult` for a date.
PanchangSource = Callable[[date], PanchangResult]


def make_panchang_source(
    cache_get: Callable[[PanchangRequest], PanchangResult],
    *,
    lat: float,
    lon: float,
    tz: str,
    month_scheme: MonthScheme,
) -> PanchangSource:
    """Bind a cache lookup to one location/scheme, yielding a `PanchangSource`.

    `cache_get` is typically `PanchangCache.get` — pass it through unchanged
    so every read goes through the read-through cache (Step 1.4), never a
    fresh engine compute.
    """

    def _source(d: date) -> PanchangResult:
        return cache_get(
            PanchangRequest(date=d, lat=lat, lon=lon, tz=tz, month_scheme=month_scheme)
        )

    return _source


def _local_tithi_index(global_index: int) -> int:
    """1-based index within the current paksha (1..15) from the 1..30 global index."""
    return ((global_index - 1) % 15) + 1


def _year_days(year: int) -> Iterable[date]:
    d = date(year, 1, 1)
    end = date(year, 12, 31)
    while d <= end:
        yield d
        d += timedelta(days=1)


def _occurrence(
    rule: FestivalRule, day: date, result: PanchangResult, note: str = ""
) -> FestivalOccurrence:
    cal = result.calendrical
    return FestivalOccurrence(
        rule_id=rule.id,
        name=rule.name,
        category=rule.category,
        date=day,
        lunar_month=cal.lunar_month,
        paksha=cal.paksha,
        tithi_name=result.tithi[0].name,
        is_adhika_month=cal.is_adhika_month,
        is_kshaya_month=cal.is_kshaya_month,
        note=note,
    )


def _matches_tithi(rule: FestivalRule, result: PanchangResult) -> bool:
    cal = result.calendrical
    if rule.lunar_month is not None and cal.lunar_month != rule.lunar_month:
        return False
    if rule.paksha is not None and cal.paksha != rule.paksha.value:
        return False
    if rule.tithi_index is not None:
        if _local_tithi_index(result.tithi[0].index) != rule.tithi_index:
            return False
    return True


def _matches_nakshatra(rule: FestivalRule, result: PanchangResult) -> bool:
    cal = result.calendrical
    if rule.lunar_month is not None and cal.lunar_month != rule.lunar_month:
        return False
    if rule.paksha is not None and cal.paksha != rule.paksha.value:
        return False
    if result.nakshatra[0].name != rule.nakshatra_name:
        return False
    if (
        rule.tithi_index is not None
        and _local_tithi_index(result.tithi[0].index) != rule.tithi_index
    ):
        return False
    return True


def _resolve_anga_rule(
    rule: FestivalRule,
    year: int,
    source: PanchangSource,
    matcher: Callable[[FestivalRule, PanchangResult], bool],
) -> list[FestivalOccurrence]:
    """Scan the year for every day matching `matcher`, then pick the
    Adhika-aware "best" occurrence.

    A Tithi can be *Vriddhi* (active at two consecutive sunrises) — by
    convention we take the first such sunrise (the "udaya-vyApti" day). A
    festival's named lunar month can also occur twice in one year (the
    Adhika instance plus the regular one); unless the rule explicitly wants
    the Adhika instance (`observe_in_adhika_month`), we prefer the regular
    (non-Adhika) occurrence and fall back to the Adhika one only if that's
    all the year contains (e.g. a Kshaya year truly skips the regular month).
    """
    matches = [
        (day, result)
        for day in _year_days(year)
        for result in [source(day)]
        if matcher(rule, result)
    ]
    if not matches:
        return []

    preferred = [
        (d, r) for d, r in matches if r.calendrical.is_adhika_month == rule.observe_in_adhika_month
    ]
    chosen_day, chosen_result = (preferred or matches)[0]
    return [_occurrence(rule, chosen_day, chosen_result)]


def _resolve_sankranti(
    rule: FestivalRule, year: int, source: PanchangSource
) -> list[FestivalOccurrence]:
    """A Sankranti is purely solar (the day the Sun's headline rashi changes
    to `rule.sun_rashi`) — independent of lunar month/scheme, so we simply
    walk consecutive days looking for the transition."""
    occurrences: list[FestivalOccurrence] = []
    prev_rashi: str | None = None
    for day in _year_days(year):
        result = source(day)
        rashi = result.calendrical.sun_rashi
        if prev_rashi is not None and prev_rashi != rashi and rashi == rule.sun_rashi:
            occurrences.append(_occurrence(rule, day, result, note=f"Sankranti into {rashi}"))
        prev_rashi = rashi
    return occurrences


def resolve_year(
    rule: FestivalRule,
    year: int,
    source: PanchangSource,
    *,
    region_tags: list[str] | None = None,
) -> list[FestivalOccurrence]:
    """Resolve `rule` to its occurrence(s) within the given Gregorian `year`,
    for the location/scheme bound into `source`.

    Returns a list because some rule kinds (e.g. Sankranti, and recurring
    observances handled in `recurring`) naturally produce more than one
    occurrence per year; Tithi/Nakshatra festival rules normally resolve to
    exactly one.
    """
    effective_rule = rule.for_region(region_tags) if region_tags else rule

    if effective_rule.kind is RuleKind.TITHI:
        return _resolve_anga_rule(effective_rule, year, source, _matches_tithi)
    if effective_rule.kind is RuleKind.NAKSHATRA:
        return _resolve_anga_rule(effective_rule, year, source, _matches_nakshatra)
    if effective_rule.kind is RuleKind.SANKRANTI:
        return _resolve_sankranti(effective_rule, year, source)

    raise ValueError(
        f"resolve_year cannot resolve kind={effective_rule.kind!r} directly — "
        "recurring observances are generated by `recurring.generate_year`"
    )
