"""Builds minimal, synthetic `PanchangResult`s for unit-testing the resolver
and recurring-observance generators without invoking the Swiss-Ephemeris
engine for a full year (slow). Only the fields the rule engine reads —
`tithi[0]`, `nakshatra[0]`, and `calendrical` — carry meaningful values;
everything else is a fixed placeholder.
"""

from __future__ import annotations

from datetime import date

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

_PLACEHOLDER_TV = TimeValue(
    iso="2024-01-01T06:00:00", hour_24="06:00:00", hour_12="06:00:00 AM", hour_24_plus="06:00:00"
)


def _span(index: int, name: str) -> AngaSpan:
    return AngaSpan(index=index, name=name, start=_PLACEHOLDER_TV, end=_PLACEHOLDER_TV)


def fake_result(
    day: date,
    *,
    tithi_index: int,
    lunar_month: str,
    paksha: str,
    nakshatra_name: str = "Ashwini",
    sun_rashi: str = "Mesha",
    is_adhika_month: bool = False,
    is_kshaya_month: bool = False,
    month_scheme: MonthScheme = MonthScheme.AMANTA,
) -> PanchangResult:
    request = PanchangRequest(
        date=day, lat=28.6139, lon=77.2090, tz="Asia/Kolkata", month_scheme=month_scheme
    )
    day_events = DayEvents(
        sunrise=_PLACEHOLDER_TV, sunset=_PLACEHOLDER_TV, moonrise=None, moonset=None
    )
    calendrical = Calendrical(
        shaka_samvat=1946,
        vikram_samvat=2081,
        gujarati_samvat=2080,
        samvatsara="Krodhi",
        ritu="Vasanta",
        ayana="Uttarayana",
        lunar_month=lunar_month,
        is_adhika_month=is_adhika_month,
        is_kshaya_month=is_kshaya_month,
        paksha=paksha,
        moon_rashi="Mesha",
        sun_rashi=sun_rashi,
    )
    return PanchangResult(
        request=request,
        sun_longitude=0.0,
        moon_longitude=0.0,
        ayanamsa_value=24.0,
        tithi=[_span(tithi_index, C.TITHI_NAMES[(tithi_index - 1) % 30])],
        nakshatra=[_span(1, nakshatra_name)],
        yoga=[_span(1, "Vishkambha")],
        karana=[_span(1, "Bava")],
        vara=_span(1, "Somavara"),
        day_events=day_events,
        muhurat=[],
        choghadiya=[],
        hora=[],
        calendrical=calendrical,
    )
