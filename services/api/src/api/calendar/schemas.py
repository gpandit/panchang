"""View-ready payload schemas for the Calendar Assembly module.

Every field needed to render a calendar cell is present here.
Clients never compute or infer Panchang values from raw data.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel

from panchang.models import AngaSpan, TimeValue


class MoonPhase(StrEnum):
    NEW_MOON = "new_moon"
    WAXING_CRESCENT = "waxing_crescent"
    FIRST_QUARTER = "first_quarter"
    WAXING_GIBBOUS = "waxing_gibbous"
    FULL_MOON = "full_moon"
    WANING_GIBBOUS = "waning_gibbous"
    LAST_QUARTER = "last_quarter"
    WANING_CRESCENT = "waning_crescent"


def moon_phase_from_tithi(global_tithi_index: int) -> MoonPhase:
    """Derive the moon-phase marker from the day's headline tithi (1–30)."""
    t = global_tithi_index
    if t == 30 or t == 0:
        return MoonPhase.NEW_MOON
    if t == 15:
        return MoonPhase.FULL_MOON
    if t == 8:
        return MoonPhase.FIRST_QUARTER
    if t == 23:
        return MoonPhase.LAST_QUARTER
    if 1 <= t <= 7:
        return MoonPhase.WAXING_CRESCENT
    if 9 <= t <= 14:
        return MoonPhase.WAXING_GIBBOUS
    if 16 <= t <= 22:
        return MoonPhase.WANING_GIBBOUS
    # 24..29
    return MoonPhase.WANING_CRESCENT


class FestivalMarker(BaseModel):
    """Thin marker for one festival/vrat on a day cell."""

    rule_id: str
    name: str
    category: str
    is_adhika_month: bool


class UserOverlay(BaseModel):
    """Presence flags for user-generated content on a day.

    Full overlay data (text, reminder fire-times) is fetched on demand.
    Stubs return empty until the Reminders & Planner modules are built.
    """

    has_note: bool = False
    has_bookmark: bool = False
    reminder_count: int = 0


class DayCell(BaseModel):
    """All data required to render one calendar cell, fully assembled server-side."""

    date: date

    # Panchang — headline anga is index 0; subsequent spans (if any) follow
    tithi: list[AngaSpan]
    nakshatra: list[AngaSpan]
    yoga: list[AngaSpan]
    karana: list[AngaSpan]
    vara: AngaSpan

    # Day events
    sunrise: TimeValue
    sunset: TimeValue
    moonrise: TimeValue | None
    moonset: TimeValue | None

    # Calendrical context
    lunar_month: str
    paksha: str
    is_adhika_month: bool
    is_kshaya_month: bool
    shaka_samvat: int
    vikram_samvat: int

    # Markers
    moon_phase: MoonPhase
    festivals: list[FestivalMarker]

    # User overlays (empty until Reminders module is built)
    overlay: UserOverlay


class WeekView(BaseModel):
    week_start: date
    week_end: date
    location: LocationParams
    days: list[DayCell]


class MonthView(BaseModel):
    year: int
    gregorian_month: int
    location: LocationParams
    days: list[DayCell]


class YearView(BaseModel):
    year: int
    location: LocationParams
    months: list[MonthView]


class RangeView(BaseModel):
    """Continuous multi-month range for calendar generator and infinite scroll.

    Supports 12–15 month spans in a single request.
    """

    start: date
    end: date
    location: LocationParams
    days: list[DayCell]


class LocationParams(BaseModel):
    """Location and computation parameters for a calendar view request."""

    lat: float
    lon: float
    tz: str
    ayanamsa: str = "lahiri"
    month_scheme: str = "amanta"
    region_tags: list[str] = []
