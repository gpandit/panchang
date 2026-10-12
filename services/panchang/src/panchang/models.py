"""Typed request/result models for the Panchang Computation Service.

These models define the public contract of the engine. Nothing outside
`services/panchang` should construct Panchang values by any other means.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum
from math import isfinite

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Ayanamsa(StrEnum):
    LAHIRI = "lahiri"


class MonthScheme(StrEnum):
    AMANTA = "amanta"
    PURNIMANTA = "purnimanta"


class PanchangRequest(BaseModel):
    """Pure input to the engine — fully determines the output."""

    date: date
    lat: float
    lon: float
    tz: str  # IANA timezone name, e.g. "Asia/Kolkata"
    ayanamsa: Ayanamsa = Ayanamsa.LAHIRI
    month_scheme: MonthScheme = MonthScheme.AMANTA


class TimeValue(BaseModel):
    """A single instant expressed in every supported display form.

    - hour_24: 0-23, wraps at midnight (standard 24h clock)
    - hour_12: 12h clock with meridiem
    - hour_24_plus: elapsed hours since the civil midnight of the opening
      sunrise; moments after the next local midnight read as 24:xx, 25:xx,
      including monotonic elapsed-hour display across a DST fold. This is
      display text, not an interval identity or `hoursFromSunrise`.
    """

    iso: str  # ISO-8601 timestamp with offset, in the requested tz
    hour_24: str  # "HH:MM:SS"
    hour_12: str  # "hh:MM:SS AM/PM"
    hour_24_plus: str  # "HH:MM:SS" where HH may exceed 23


class CanonicalInterval(BaseModel):
    """Full interval identity; hoursFromSunrise is the END instant's elapsed UTC hours.

    This deliberately permits negative and >24 values (pre-sunrise and carry-over).
    The offset describes the local clock at the interval's start; an interval can
    cross a DST boundary, so consumers must convert each UTC endpoint separately.
    """

    model_config = ConfigDict(populate_by_name=True)

    start_utc: datetime = Field(alias="startUtc")
    end_utc: datetime = Field(alias="endUtc")
    local_offset_minutes: int = Field(alias="localOffsetMinutes", ge=-1440, le=1440)
    hours_from_sunrise: float = Field(alias="hoursFromSunrise")
    flags: list[str]

    @model_validator(mode="after")
    def validate_interval(self) -> CanonicalInterval:
        if self.start_utc.tzinfo is None or self.end_utc.tzinfo is None:
            raise ValueError("interval endpoints must have UTC timezone")
        if self.start_utc.utcoffset() != UTC.utcoffset(
            None
        ) or self.end_utc.utcoffset() != UTC.utcoffset(None):
            raise ValueError("interval endpoints must be UTC")
        if self.end_utc <= self.start_utc:
            raise ValueError("interval end must be after start")
        if not isfinite(self.hours_from_sunrise):
            raise ValueError("hoursFromSunrise must be finite")
        return self


class AngaSpan(CanonicalInterval):
    """One occurrence of an anga (Tithi/Nakshatra/Yoga/Karana/Vara) with its
    boundary timestamps, clipped to the Panchang day."""

    index: int  # 1-based index within its cycle
    name: str
    start: TimeValue | None  # None if the span starts before the Panchang day
    end: TimeValue | None  # None if the span ends after the Panchang day


class MuhuratPeriod(CanonicalInterval):
    name: str
    start: TimeValue
    end: TimeValue


class Choghadiya(CanonicalInterval):
    name: str
    start: TimeValue
    end: TimeValue
    is_day: bool


class DayEvents(BaseModel):
    sunrise: TimeValue
    sunset: TimeValue
    moonrise: TimeValue | None
    moonset: TimeValue | None
    flags: list[str] = Field(default_factory=list)


class Calendrical(BaseModel):
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


class PanchangResult(BaseModel):
    """The complete, deterministic Panchang for one (date, location, settings)."""

    request: PanchangRequest
    flags: list[str] = Field(default_factory=list)

    sun_longitude: float
    moon_longitude: float
    ayanamsa_value: float

    tithi: list[AngaSpan]
    nakshatra: list[AngaSpan]
    yoga: list[AngaSpan]
    karana: list[AngaSpan]
    vara: AngaSpan

    day_events: DayEvents
    muhurat: list[MuhuratPeriod]
    choghadiya: list[Choghadiya]
    hora: list[MuhuratPeriod]

    calendrical: Calendrical
