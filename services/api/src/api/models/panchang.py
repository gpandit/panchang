"""Request / response models for the Panchang v1 endpoints.

These are the API-layer shapes. The gateway maps them from the internal
PanchangResult produced by services/panchang.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, field_validator


class DailyPanchangRequest(BaseModel):
    """Query parameters for GET /v1/panchang/daily."""

    date: date
    lat: float
    lon: float
    tz: str
    ayanamsa: str = "lahiri"
    month_scheme: str = "amanta"

    @field_validator("lat")
    @classmethod
    def validate_lat(cls, v: float) -> float:
        if not -90 <= v <= 90:
            raise ValueError("lat must be between -90 and 90")
        return v

    @field_validator("lon")
    @classmethod
    def validate_lon(cls, v: float) -> float:
        if not -180 <= v <= 180:
            raise ValueError("lon must be between -180 and 180")
        return v


class TimeValueOut(BaseModel):
    iso: str
    hour_24: str
    hour_12: str
    hour_24_plus: str


class AngaSpanOut(BaseModel):
    index: int
    name: str
    start: TimeValueOut | None
    end: TimeValueOut | None


class DayEventsOut(BaseModel):
    sunrise: TimeValueOut
    sunset: TimeValueOut
    moonrise: TimeValueOut | None
    moonset: TimeValueOut | None


class CalendricalOut(BaseModel):
    shaka_samvat: int
    vikram_samvat: int
    gujarati_samvat: int
    samvatsara: str
    ritu: str
    ayana: str
    lunar_month: str
    is_adhika_month: bool
    is_kshaya_month: bool
    paksha: str
    moon_rashi: str
    sun_rashi: str


class PeriodOut(BaseModel):
    name: str
    start: TimeValueOut
    end: TimeValueOut


class ChoghadiyaOut(BaseModel):
    name: str
    start: TimeValueOut
    end: TimeValueOut
    is_day: bool


class DailyPanchangOut(BaseModel):
    """Full Panchang for one (date, location, settings) — the primary API payload."""

    date: str  # "YYYY-MM-DD"
    lat: float
    lon: float
    tz: str
    ayanamsa: str
    month_scheme: str

    sun_longitude: float
    moon_longitude: float
    ayanamsa_value: float

    tithi: list[AngaSpanOut]
    nakshatra: list[AngaSpanOut]
    yoga: list[AngaSpanOut]
    karana: list[AngaSpanOut]
    vara: AngaSpanOut

    day_events: DayEventsOut
    muhurat: list[PeriodOut]
    choghadiya: list[ChoghadiyaOut]
    hora: list[PeriodOut]
    calendrical: CalendricalOut

    # Cache metadata injected by the gateway layer
    cached: bool = False


class MonthCalendarRequest(BaseModel):
    year: int
    month: int  # 1–12
    lat: float
    lon: float
    tz: str
    ayanamsa: str = "lahiri"
    month_scheme: str = "amanta"


class MonthCalendarOut(BaseModel):
    year: int
    month: int
    days: list[DailyPanchangOut]
