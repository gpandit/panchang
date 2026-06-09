"""Typed request/result models for the Panchang Computation Service.

These models define the public contract of the engine. Nothing outside
`services/panchang` should construct Panchang values by any other means.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel


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

    - hour_24: 0–23, wraps at midnight (standard 24h clock)
    - hour_12: 12h clock with meridiem
    - hour_24_plus: hours past the start of the Panchang day (sunrise), so
      a moment after local midnight but before the next sunrise reads as
      24:xx, 25:xx, ... — a first-class representation, not a display flag.
    """

    iso: str  # ISO-8601 timestamp with offset, in the requested tz
    hour_24: str  # "HH:MM:SS"
    hour_12: str  # "hh:MM:SS AM/PM"
    hour_24_plus: str  # "HH:MM:SS" where HH may exceed 23


class AngaSpan(BaseModel):
    """One occurrence of an anga (Tithi/Nakshatra/Yoga/Karana/Vara) with its
    boundary timestamps, clipped to the Panchang day."""

    index: int  # 1-based index within its cycle
    name: str
    start: TimeValue | None  # None if the span starts before the Panchang day
    end: TimeValue | None  # None if the span ends after the Panchang day


class MuhuratPeriod(BaseModel):
    name: str
    start: TimeValue
    end: TimeValue


class Choghadiya(BaseModel):
    name: str
    start: TimeValue
    end: TimeValue
    is_day: bool


class DayEvents(BaseModel):
    sunrise: TimeValue
    sunset: TimeValue
    moonrise: TimeValue | None
    moonset: TimeValue | None


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
