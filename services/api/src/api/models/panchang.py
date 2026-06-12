"""Request / response models for the Panchang v1 endpoints.

These are the API-layer shapes. The gateway maps them from the internal
PanchangResult produced by services/panchang.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    month: int  # 1-12
    lat: float
    lon: float
    tz: str
    ayanamsa: str = "lahiri"
    month_scheme: str = "amanta"


class MonthCalendarOut(BaseModel):
    year: int
    month: int
    days: list[DailyPanchangOut]


# ─── Today / Daily view model ────────────────────────────────────────────────
# View-ready shapes for GET /v1/panchang/daily, matching
# @pandit/api-client-ts's DailyPanchangView. Fields are derived by reformatting
# the already-computed DailyPanchangOut — no Panchang values are recomputed.


class PanchangElementOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    key: str
    label: str
    value: str
    secondary_value: str | None = Field(default=None, alias="secondaryValue")
    group: Literal["core", "solar", "lunar", "other"]
    explanation: str | None = None


class MuhuratWindowOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    start_time: str = Field(alias="startTime")
    end_time: str = Field(alias="endTime")
    type: Literal["auspicious", "inauspicious"]
    description: str | None = None


class FestivalViewOut(BaseModel):
    name: str
    type: Literal["festival", "vrat", "ekadashi", "other"]
    description: str | None = None
    significance: str | None = None


class AdvisoryOut(BaseModel):
    category: Literal["good", "avoid"]
    label: str
    detail: str | None = None


class DailyHighlightOut(BaseModel):
    label: str
    value: str
    detail: str | None = None


class DharmaCardOut(BaseModel):
    title: str
    body: str
    attribution: str | None = None


class DailyPanchangViewOut(BaseModel):
    """View-ready daily Panchang payload for GET /v1/panchang/daily."""

    model_config = ConfigDict(populate_by_name=True)

    date: str
    lat: float
    lon: float
    tz: str
    location_label: str = Field(alias="locationLabel")

    summary_title: str = Field(alias="summaryTitle")
    panchang_hindi_date: str = Field(alias="panchangHindiDate")

    elements: list[PanchangElementOut]

    sunrise: str | None
    sunset: str | None
    moonrise: str | None
    moonset: str | None

    muhurats: list[MuhuratWindowOut]
    festivals: list[FestivalViewOut]
    advisories: list[AdvisoryOut]
    highlights: list[DailyHighlightOut]
    dharma_card: DharmaCardOut | None = Field(default=None, alias="dharmaCard")

    leap_month_flag: Literal["adhika", "kshaya"] | None = Field(default=None, alias="leapMonthFlag")
    cached_at: str = Field(alias="cachedAt")
