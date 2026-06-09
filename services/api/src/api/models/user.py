"""User profile, location, and vault models for the v1 API."""

from __future__ import annotations

from pydantic import BaseModel


class LocationIn(BaseModel):
    name: str
    lat: float
    lon: float
    tz: str
    is_default: bool = False


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
    display_name: str | None = None
    default_ayanamsa: str | None = None
    default_month_scheme: str | None = None
