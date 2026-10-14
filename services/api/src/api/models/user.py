"""User profile, location, and vault models for the v1 API."""

from __future__ import annotations

from datetime import date
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LocationIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=160)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    tz: str = Field(min_length=1, max_length=64)
    is_default: bool = False

    @field_validator("tz")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("tz must be a valid IANA timezone") from exc
        return value


class LocationOut(LocationIn):
    id: str


class ProfileOut(BaseModel):
    user_id: str
    email: str | None
    display_name: str | None
    default_ayanamsa: str
    default_month_scheme: str
    locations: list[LocationOut]


class ProfileUpdateIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    display_name: str | None = Field(default=None, max_length=200)
    default_ayanamsa: str | None = Field(default=None, min_length=1, max_length=32)
    default_month_scheme: str | None = Field(default=None, min_length=1, max_length=32)

    @field_validator("default_ayanamsa")
    @classmethod
    def validate_ayanamsa(cls, value: str | None) -> str | None:
        if value is not None and value.lower() != "lahiri":
            raise ValueError("default_ayanamsa must be lahiri")
        return value.lower() if value is not None else value

    @field_validator("default_month_scheme")
    @classmethod
    def validate_month_scheme(cls, value: str | None) -> str | None:
        if value is not None and value.lower() not in {"amanta", "purnimanta"}:
            raise ValueError("default_month_scheme must be amanta or purnimanta")
        return value.lower() if value is not None else value


class BirthDetailsIn(BaseModel):
    """Sensitive values accepted by the Vault boundary and never returned."""

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="forbid",
    )

    date_of_birth: date = Field(alias="dateOfBirth")
    time_of_birth: str | None = Field(default=None, alias="timeOfBirth", pattern=r"^\d{2}:\d{2}$")
    place_of_birth: dict[str, Any] | None = Field(default=None, alias="placeOfBirth")

    @field_validator("place_of_birth")
    @classmethod
    def validate_place(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        # Place details are Vault-only, but rejecting malformed coordinates here
        # avoids persisting an unusable sensitive record.
        if "lat" in value and not -90 <= float(value["lat"]) <= 90:
            raise ValueError("placeOfBirth.lat must be between -90 and 90")
        if "lon" in value and not -180 <= float(value["lon"]) <= 180:
            raise ValueError("placeOfBirth.lon must be between -180 and 180")
        if "tz" in value:
            try:
                ZoneInfo(str(value["tz"]))
            except (ZoneInfoNotFoundError, ValueError) as exc:
                raise ValueError("placeOfBirth.tz must be a valid IANA timezone") from exc
        return value
