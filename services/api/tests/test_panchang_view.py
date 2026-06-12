"""Tests: to_daily_panchang_view() — DailyPanchangOut -> DailyPanchangViewOut mapping."""

from __future__ import annotations

from datetime import datetime

from api.models.panchang import (
    AngaSpanOut,
    CalendricalOut,
    ChoghadiyaOut,
    DailyPanchangOut,
    DayEventsOut,
    PeriodOut,
    TimeValueOut,
)
from api.panchang_view import to_daily_panchang_view


def _time(t: str) -> TimeValueOut:
    return TimeValueOut(iso=t, hour_24=t[:5], hour_12=t[:5], hour_24_plus=t[:5])


def _anga(name: str, idx: int, end: TimeValueOut | None = None) -> AngaSpanOut:
    return AngaSpanOut(index=idx, name=name, start=None, end=end)


_DEFAULT_MOONRISE = _time("08:00:00+05:30")
_DEFAULT_MOONSET = _time("20:00:00+05:30")
_DEFAULT_TITHI_END = _time("14:32:00+05:30")


_DEFAULT_MUHURAT = [PeriodOut(name="Brahma Muhurta", start=_time("05:30"), end=_time("06:15"))]


def _sample(
    *,
    moonrise: TimeValueOut | None = _DEFAULT_MOONRISE,
    moonset: TimeValueOut | None = _DEFAULT_MOONSET,
    tithi_end: TimeValueOut | None = _DEFAULT_TITHI_END,
    is_adhika_month: bool = False,
    is_kshaya_month: bool = False,
    muhurat: list[PeriodOut] | None = None,
) -> DailyPanchangOut:
    return DailyPanchangOut(
        date="2025-01-14",
        lat=28.6139,
        lon=77.2090,
        tz="Asia/Kolkata",
        ayanamsa="lahiri",
        month_scheme="amanta",
        sun_longitude=270.0,
        moon_longitude=45.0,
        ayanamsa_value=23.8,
        tithi=[_anga("Pratipada", 1, end=tithi_end)],
        nakshatra=[_anga("Ashwini", 1)],
        yoga=[_anga("Vishkambha", 1)],
        karana=[_anga("Bava", 1)],
        vara=_anga("Mangalvara", 3),
        day_events=DayEventsOut(
            sunrise=_time("07:15:00+05:30"),
            sunset=_time("17:45:00+05:30"),
            moonrise=moonrise,
            moonset=moonset,
        ),
        muhurat=muhurat if muhurat is not None else _DEFAULT_MUHURAT,
        choghadiya=[
            ChoghadiyaOut(name="Udveg", start=_time("07:15"), end=_time("08:37"), is_day=True)
        ],
        hora=[PeriodOut(name="Mars", start=_time("07:15"), end=_time("08:15"))],
        calendrical=CalendricalOut(
            shaka_samvat=1946,
            vikram_samvat=2081,
            gujarati_samvat=2081,
            samvatsara="Krodhi",
            ritu="Shishira",
            ayana="Uttarayana",
            lunar_month="Pausha",
            is_adhika_month=is_adhika_month,
            is_kshaya_month=is_kshaya_month,
            paksha="Krishna",
            moon_rashi="Mesha",
            sun_rashi="Makara",
        ),
        cached=False,
    )


def test_elements_include_core_solar_lunar_and_other_groups() -> None:
    view = to_daily_panchang_view(_sample())
    groups = {el.group for el in view.elements}
    assert groups == {"core", "solar", "lunar", "other"}

    by_key = {el.key: el for el in view.elements}
    assert by_key["tithi"].value == "Pratipada"
    assert by_key["tithi"].group == "core"
    assert by_key["vara"].value == "Mangalvara"
    assert by_key["sun_rashi"].value == "Makara"
    assert by_key["moon_rashi"].value == "Mesha"
    assert by_key["vikram_samvat"].value == "2081"


def test_secondary_value_set_when_span_has_end() -> None:
    view = to_daily_panchang_view(_sample())
    by_key = {el.key: el for el in view.elements}
    assert by_key["tithi"].secondary_value == "ends:14:32:00+05:30"


def test_secondary_value_none_when_span_has_no_end() -> None:
    view = to_daily_panchang_view(_sample(tithi_end=None))
    by_key = {el.key: el for el in view.elements}
    assert by_key["tithi"].secondary_value is None


def test_vara_has_no_secondary_value() -> None:
    view = to_daily_panchang_view(_sample())
    by_key = {el.key: el for el in view.elements}
    assert by_key["vara"].secondary_value is None


def test_muhurats_mapped_as_auspicious() -> None:
    view = to_daily_panchang_view(_sample())
    assert len(view.muhurats) == 1
    m = view.muhurats[0]
    assert m.name == "Brahma Muhurta"
    assert m.start_time == "05:30"
    assert m.end_time == "06:15"
    assert m.type == "auspicious"


def test_muhurats_classify_avoid_windows_as_inauspicious() -> None:
    view = to_daily_panchang_view(
        _sample(
            muhurat=[
                PeriodOut(name="Brahma Muhurta", start=_time("05:30"), end=_time("06:15")),
                PeriodOut(name="Abhijit Muhurta", start=_time("11:48"), end=_time("12:36")),
                PeriodOut(name="Rahu Kalam", start=_time("09:00"), end=_time("10:30")),
                PeriodOut(name="Yamaganda", start=_time("12:00"), end=_time("13:30")),
                PeriodOut(name="Gulika Kalam", start=_time("15:00"), end=_time("16:30")),
                PeriodOut(name="Dur Muhurat", start=_time("08:00"), end=_time("08:45")),
            ]
        )
    )
    by_name = {m.name: m.type for m in view.muhurats}
    assert by_name["Brahma Muhurta"] == "auspicious"
    assert by_name["Abhijit Muhurta"] == "auspicious"
    assert by_name["Rahu Kalam"] == "inauspicious"
    assert by_name["Yamaganda"] == "inauspicious"
    assert by_name["Gulika Kalam"] == "inauspicious"
    assert by_name["Dur Muhurat"] == "inauspicious"


def test_sun_and_moon_event_times() -> None:
    view = to_daily_panchang_view(_sample())
    assert view.sunrise == "07:15:00+05:30"
    assert view.sunset == "17:45:00+05:30"
    assert view.moonrise == "08:00:00+05:30"
    assert view.moonset == "20:00:00+05:30"


def test_moonrise_and_moonset_null_when_absent() -> None:
    view = to_daily_panchang_view(_sample(moonrise=None, moonset=None))
    assert view.moonrise is None
    assert view.moonset is None


def test_summary_title_and_hindi_date() -> None:
    view = to_daily_panchang_view(_sample())
    assert view.summary_title == "Mangalvara · Pratipada"
    assert view.panchang_hindi_date == "Pausha · Krishna Paksha"


def test_leap_month_flag_defaults_to_none() -> None:
    view = to_daily_panchang_view(_sample())
    assert view.leap_month_flag is None


def test_leap_month_flag_adhika() -> None:
    view = to_daily_panchang_view(_sample(is_adhika_month=True))
    assert view.leap_month_flag == "adhika"


def test_leap_month_flag_kshaya() -> None:
    view = to_daily_panchang_view(_sample(is_kshaya_month=True))
    assert view.leap_month_flag == "kshaya"


def test_unimplemented_sections_are_empty() -> None:
    view = to_daily_panchang_view(_sample())
    assert view.festivals == []
    assert view.advisories == []
    assert view.highlights == []
    assert view.dharma_card is None


def test_cached_at_is_iso_timestamp() -> None:
    view = to_daily_panchang_view(_sample())
    # Should be parseable as an ISO 8601 timestamp.
    datetime.fromisoformat(view.cached_at)
