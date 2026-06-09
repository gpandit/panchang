"""Calendar Assembly Service — Step 2.4.

Composes view-ready payloads from cached Panchang + resolved festivals +
user overlays. Never computes astronomy directly.

Architecture north-star §3 (component 02): "Return view-ready payloads so
clients do no Panchang math."
"""

from __future__ import annotations

import calendar as _cal
from collections import defaultdict
from datetime import date, timedelta

from festivals.models import FestivalOccurrence, FestivalRule
from festivals.resolver import make_panchang_source, resolve_year

from api.calendar.schemas import (
    DayCell,
    FestivalMarker,
    LocationParams,
    MonthView,
    RangeView,
    UserOverlay,
    WeekView,
    YearView,
    moon_phase_from_tithi,
)
from panchang.cache import PanchangCache
from panchang.models import Ayanamsa, MonthScheme, PanchangRequest, PanchangResult


class CalendarService:
    """Assembles all calendar views from cached Panchang and resolved festivals.

    `festival_rules` is the authoritative catalogue; the CMS module owns
    growing it. Pass an empty list to omit festival markers (e.g. in tests
    that only care about Panchang data).
    """

    def __init__(
        self,
        panchang_cache: PanchangCache,
        festival_rules: list[FestivalRule] | None = None,
    ) -> None:
        self._cache = panchang_cache
        self._rules = festival_rules or []

    # ── internal helpers ──────────────────────────────────────────────────

    def _panchang(self, d: date, loc: LocationParams) -> PanchangResult:
        return self._cache.get(
            PanchangRequest(
                date=d,
                lat=loc.lat,
                lon=loc.lon,
                tz=loc.tz,
                ayanamsa=Ayanamsa(loc.ayanamsa),
                month_scheme=MonthScheme(loc.month_scheme),
            )
        )

    def _festival_index(
        self, start: date, end: date, loc: LocationParams
    ) -> dict[date, list[FestivalOccurrence]]:
        """Build a date→occurrences map for all years covered by [start, end]."""
        index: dict[date, list[FestivalOccurrence]] = defaultdict(list)
        if not self._rules:
            return index

        source = make_panchang_source(
            self._cache.get,
            lat=loc.lat,
            lon=loc.lon,
            tz=loc.tz,
            month_scheme=MonthScheme(loc.month_scheme),
        )

        years = range(start.year, end.year + 1)
        for year in years:
            for rule in self._rules:
                try:
                    occurrences = resolve_year(
                        rule, year, source, region_tags=loc.region_tags or None
                    )
                except Exception:
                    # A single rule failure must not break the whole view
                    continue
                for occ in occurrences:
                    if start <= occ.date <= end:
                        index[occ.date].append(occ)

        return index

    def _cell(
        self,
        d: date,
        loc: LocationParams,
        result: PanchangResult,
        occurrences: list[FestivalOccurrence],
        overlay: UserOverlay | None = None,
    ) -> DayCell:
        tithi_index = result.tithi[0].index if result.tithi else 0
        return DayCell(
            date=d,
            tithi=result.tithi,
            nakshatra=result.nakshatra,
            yoga=result.yoga,
            karana=result.karana,
            vara=result.vara,
            sunrise=result.day_events.sunrise,
            sunset=result.day_events.sunset,
            moonrise=result.day_events.moonrise,
            moonset=result.day_events.moonset,
            lunar_month=result.calendrical.lunar_month,
            paksha=result.calendrical.paksha,
            is_adhika_month=result.calendrical.is_adhika_month,
            is_kshaya_month=result.calendrical.is_kshaya_month,
            shaka_samvat=result.calendrical.shaka_samvat,
            vikram_samvat=result.calendrical.vikram_samvat,
            moon_phase=moon_phase_from_tithi(tithi_index),
            festivals=[
                FestivalMarker(
                    rule_id=occ.rule_id,
                    name=occ.name,
                    category=occ.category,
                    is_adhika_month=occ.is_adhika_month,
                )
                for occ in occurrences
            ],
            overlay=overlay or UserOverlay(),
        )

    def _cells_for_range(self, start: date, end: date, loc: LocationParams) -> list[DayCell]:
        fest_index = self._festival_index(start, end, loc)
        cells: list[DayCell] = []
        d = start
        while d <= end:
            result = self._panchang(d, loc)
            cells.append(self._cell(d, loc, result, fest_index.get(d, [])))
            d += timedelta(days=1)
        return cells

    # ── public view builders ──────────────────────────────────────────────

    def day(self, d: date, loc: LocationParams) -> DayCell:
        """Single day view."""
        result = self._panchang(d, loc)
        fest_index = self._festival_index(d, d, loc)
        return self._cell(d, loc, result, fest_index.get(d, []))

    def week(self, d: date, loc: LocationParams) -> WeekView:
        """Week containing `d` (Monday–Sunday)."""
        week_start = d - timedelta(days=d.weekday())
        week_end = week_start + timedelta(days=6)
        return WeekView(
            week_start=week_start,
            week_end=week_end,
            location=loc,
            days=self._cells_for_range(week_start, week_end, loc),
        )

    def month(self, year: int, gregorian_month: int, loc: LocationParams) -> MonthView:
        """Full Gregorian calendar month view."""
        _, last_day = _cal.monthrange(year, gregorian_month)
        start = date(year, gregorian_month, 1)
        end = date(year, gregorian_month, last_day)
        return MonthView(
            year=year,
            gregorian_month=gregorian_month,
            location=loc,
            days=self._cells_for_range(start, end, loc),
        )

    def year(self, year: int, loc: LocationParams) -> YearView:
        """Full Gregorian year view (12 months)."""
        return YearView(
            year=year,
            location=loc,
            months=[self.month(year, m, loc) for m in range(1, 13)],
        )

    def range(self, start: date, end: date, loc: LocationParams) -> RangeView:
        """Continuous date-range view (supports 12–15-month spans).

        Raises ValueError if the range exceeds 550 days (~18 months) to
        prevent runaway computation.
        """
        span = (end - start).days + 1
        if span > 550:
            raise ValueError(
                f"Range span {span} days exceeds the 550-day maximum. "
                "Request multiple smaller ranges instead."
            )
        return RangeView(
            start=start,
            end=end,
            location=loc,
            days=self._cells_for_range(start, end, loc),
        )
