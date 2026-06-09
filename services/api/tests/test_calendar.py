"""Tests for the Calendar Assembly module (Step 2.4).

Uses a deterministic stub PanchangCache so Swiss Ephemeris is never invoked.
The stub returns pre-built PanchangResults keyed by date, falling back to a
synthetic default so every date in a range resolves without error.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from festivals.models import FestivalRule, Paksha, RuleKind

from api.calendar.schemas import MoonPhase, moon_phase_from_tithi
from api.calendar.service import CalendarService
from panchang import constants as C
from panchang.models import (
    AngaSpan,
    Calendrical,
    DayEvents,
    MonthScheme,
    PanchangRequest,
    PanchangResult,
    TimeValue,
)

# ── helpers ────────────────────────────────────────────────────────────────────

_TV = TimeValue(
    iso="2024-11-01T06:00:00+05:30",
    hour_24="06:00:00",
    hour_12="06:00:00 AM",
    hour_24_plus="06:00:00",
)


def _span(index: int, name: str) -> AngaSpan:
    return AngaSpan(index=index, name=name, start=_TV, end=_TV)


def _make_result(
    day: date,
    *,
    tithi_index: int = 1,
    lunar_month: str = "Kartika",
    paksha: str = "Shukla Paksha",
    sun_rashi: str = "Tula",
    is_adhika: bool = False,
) -> PanchangResult:
    return PanchangResult(
        request=PanchangRequest(
            date=day, lat=28.6, lon=77.2, tz="Asia/Kolkata", month_scheme=MonthScheme.AMANTA
        ),
        sun_longitude=180.0,
        moon_longitude=0.0,
        ayanamsa_value=24.0,
        tithi=[_span(tithi_index, C.TITHI_NAMES[(tithi_index - 1) % 30])],
        nakshatra=[_span(1, "Ashwini")],
        yoga=[_span(1, "Vishkambha")],
        karana=[_span(1, "Bava")],
        vara=_span(1, "Somavara"),
        day_events=DayEvents(sunrise=_TV, sunset=_TV, moonrise=None, moonset=None),
        muhurat=[],
        choghadiya=[],
        hora=[],
        calendrical=Calendrical(
            shaka_samvat=1946,
            vikram_samvat=2081,
            gujarati_samvat=2080,
            samvatsara="Krodhi",
            ritu="Sharad",
            ayana="Dakshinayana",
            lunar_month=lunar_month,
            is_adhika_month=is_adhika,
            is_kshaya_month=False,
            paksha=paksha,
            moon_rashi="Mesha",
            sun_rashi=sun_rashi,
        ),
    )


class StubCache:
    """Thin stand-in for PanchangCache; returns pre-seeded results or a default."""

    def __init__(self, seed: dict[date, PanchangResult] | None = None) -> None:
        self._seed = seed or {}

    def get(self, request: PanchangRequest) -> PanchangResult:
        return self._seed.get(request.date, _make_result(request.date))


# ── moon phase helper ──────────────────────────────────────────────────────────


class TestMoonPhase:
    def test_new_moon(self):
        assert moon_phase_from_tithi(30) is MoonPhase.NEW_MOON

    def test_full_moon(self):
        assert moon_phase_from_tithi(15) is MoonPhase.FULL_MOON

    def test_first_quarter(self):
        assert moon_phase_from_tithi(8) is MoonPhase.FIRST_QUARTER

    def test_last_quarter(self):
        assert moon_phase_from_tithi(23) is MoonPhase.LAST_QUARTER

    def test_waxing_crescent(self):
        for t in range(1, 8):
            assert moon_phase_from_tithi(t) is MoonPhase.WAXING_CRESCENT

    def test_waxing_gibbous(self):
        for t in range(9, 15):
            assert moon_phase_from_tithi(t) is MoonPhase.WAXING_GIBBOUS

    def test_waning_gibbous(self):
        for t in range(16, 23):
            assert moon_phase_from_tithi(t) is MoonPhase.WANING_GIBBOUS

    def test_waning_crescent(self):
        for t in range(24, 30):
            assert moon_phase_from_tithi(t) is MoonPhase.WANING_CRESCENT


# ── CalendarService ────────────────────────────────────────────────────────────


def _loc_params(**kwargs):
    from api.calendar.schemas import LocationParams

    return LocationParams(lat=28.6, lon=77.2, tz="Asia/Kolkata", **kwargs)


LOC = _loc_params()


class TestDayView:
    def test_returns_day_cell(self):
        svc = CalendarService(StubCache())
        cell = svc.day(date(2024, 11, 1), LOC)
        assert cell.date == date(2024, 11, 1)

    def test_tithi_present(self):
        seed = {date(2024, 11, 1): _make_result(date(2024, 11, 1), tithi_index=15)}
        svc = CalendarService(StubCache(seed))
        cell = svc.day(date(2024, 11, 1), LOC)
        assert len(cell.tithi) == 1
        assert cell.tithi[0].index == 15
        assert cell.moon_phase is MoonPhase.FULL_MOON

    def test_festival_marker_attached(self):
        # Diwali rule: Ashwina Krishna Paksha Amavasya (tithi_index=15 in paksha = global 30)
        diwali_day = date(2024, 11, 1)
        seed = {
            diwali_day: _make_result(
                diwali_day,
                tithi_index=30,
                lunar_month="Ashwina",
                paksha="Krishna Paksha",
            )
        }
        diwali_rule = FestivalRule(
            id="diwali",
            name="Diwali",
            kind=RuleKind.TITHI,
            category="festival",
            lunar_month="Ashwina",
            paksha=Paksha.KRISHNA,
            tithi_index=15,  # local within paksha
        )
        svc = CalendarService(StubCache(seed), [diwali_rule])
        cell = svc.day(diwali_day, LOC)
        assert any(f.rule_id == "diwali" for f in cell.festivals)

    def test_overlay_empty_by_default(self):
        svc = CalendarService(StubCache())
        cell = svc.day(date(2024, 11, 1), LOC)
        assert not cell.overlay.has_note
        assert not cell.overlay.has_bookmark
        assert cell.overlay.reminder_count == 0


class TestWeekView:
    def test_week_has_seven_days(self):
        svc = CalendarService(StubCache())
        view = svc.week(date(2024, 11, 6), LOC)  # Wednesday
        assert len(view.days) == 7

    def test_week_starts_on_monday(self):
        svc = CalendarService(StubCache())
        view = svc.week(date(2024, 11, 6), LOC)
        assert view.week_start.weekday() == 0  # Monday
        assert view.week_end.weekday() == 6  # Sunday

    def test_all_days_have_panchang(self):
        svc = CalendarService(StubCache())
        view = svc.week(date(2024, 11, 1), LOC)
        for cell in view.days:
            assert cell.tithi, f"Missing tithi on {cell.date}"
            assert cell.vara is not None


class TestMonthView:
    def test_november_has_30_days(self):
        svc = CalendarService(StubCache())
        view = svc.month(2024, 11, LOC)
        assert len(view.days) == 30

    def test_february_leap_year(self):
        svc = CalendarService(StubCache())
        view = svc.month(2024, 2, LOC)
        assert len(view.days) == 29

    def test_february_non_leap_year(self):
        svc = CalendarService(StubCache())
        view = svc.month(2023, 2, LOC)
        assert len(view.days) == 28

    def test_each_day_has_correct_date(self):
        svc = CalendarService(StubCache())
        view = svc.month(2024, 3, LOC)
        for i, cell in enumerate(view.days):
            assert cell.date == date(2024, 3, i + 1)

    def test_festivals_appear_in_month(self):
        holi_day = date(2024, 3, 25)
        seed = {
            holi_day: _make_result(
                holi_day,
                tithi_index=15,
                lunar_month="Phalguna",
                paksha="Shukla Paksha",
            )
        }
        holi_rule = FestivalRule(
            id="holi",
            name="Holi",
            kind=RuleKind.TITHI,
            category="festival",
            lunar_month="Phalguna",
            paksha=Paksha.SHUKLA,
            tithi_index=15,
        )
        svc = CalendarService(StubCache(seed), [holi_rule])
        view = svc.month(2024, 3, LOC)
        holi_cell = next(c for c in view.days if c.date == holi_day)
        assert any(f.rule_id == "holi" for f in holi_cell.festivals)

    def test_tithis_present_all_days(self):
        svc = CalendarService(StubCache())
        view = svc.month(2024, 11, LOC)
        for cell in view.days:
            assert cell.tithi

    def test_moon_phase_markers_present(self):
        svc = CalendarService(StubCache())
        view = svc.month(2024, 11, LOC)
        for cell in view.days:
            assert isinstance(cell.moon_phase, MoonPhase)

    def test_purnimanta_scheme_accepted(self):
        loc_p = _loc_params(month_scheme="purnimanta")
        svc = CalendarService(StubCache())
        view = svc.month(2024, 11, loc_p)
        assert len(view.days) == 30

    def test_amanta_and_purnimanta_differ_in_lunar_month(self):
        """Views under different schemes may report different lunar months for the same day."""

        # Build two stubs that return different lunar_month values per scheme —
        # the cache is scheme-keyed in production; here we just assert the
        # service wires the month_scheme through to the request.
        class SchemeSensitiveCache:
            def get(self, request: PanchangRequest) -> PanchangResult:
                lm = "Kartika" if request.month_scheme == MonthScheme.AMANTA else "Margashirsha"
                return _make_result(request.date, lunar_month=lm)

        svc = CalendarService(SchemeSensitiveCache())  # type: ignore[arg-type]
        amanta = svc.month(2024, 11, _loc_params(month_scheme="amanta"))
        purnimanta = svc.month(2024, 11, _loc_params(month_scheme="purnimanta"))
        amanta_months = {c.lunar_month for c in amanta.days}
        purnimanta_months = {c.lunar_month for c in purnimanta.days}
        assert amanta_months != purnimanta_months


class TestYearView:
    def test_year_has_12_months(self):
        svc = CalendarService(StubCache())
        view = svc.year(2024, LOC)
        assert len(view.months) == 12

    def test_year_months_in_order(self):
        svc = CalendarService(StubCache())
        view = svc.year(2024, LOC)
        for i, mv in enumerate(view.months, start=1):
            assert mv.gregorian_month == i


class TestRangeView:
    def test_12_month_range(self):
        start = date(2024, 1, 1)
        end = date(2024, 12, 31)
        svc = CalendarService(StubCache())
        view = svc.range(start, end, LOC)
        assert len(view.days) == 366  # 2024 is a leap year

    def test_15_month_range(self):
        start = date(2024, 1, 1)
        end = date(2025, 3, 31)
        svc = CalendarService(StubCache())
        view = svc.range(start, end, LOC)
        expected = (end - start).days + 1
        assert len(view.days) == expected

    def test_range_exceeding_max_raises(self):
        svc = CalendarService(StubCache())
        with pytest.raises(ValueError, match="550"):
            svc.range(date(2024, 1, 1), date(2025, 7, 10), LOC)

    def test_days_contiguous(self):
        start = date(2024, 6, 1)
        end = date(2024, 8, 31)
        svc = CalendarService(StubCache())
        view = svc.range(start, end, LOC)
        for i in range(1, len(view.days)):
            assert view.days[i].date == view.days[i - 1].date + timedelta(days=1)
