"""Pydantic request/response schemas for the Users API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, EmailStr

from api.users.models import AuthProvider, CalendarSystem, TimeForm


class SignUpWithPassword(BaseModel):
    email: EmailStr | None = None
    phone: str | None = None
    password: str
    display_name: str | None = None


class SignUpWithOAuth(BaseModel):
    provider: AuthProvider  # GOOGLE | APPLE
    identity_token: str
    display_name: str | None = None


class LoginWithPassword(BaseModel):
    email: EmailStr | None = None
    phone: str | None = None
    password: str


class TokenPairOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class PreferencesUpdate(BaseModel):
    display_name: str | None = None
    preferred_calendar_system: CalendarSystem | None = None
    language: str | None = None
    time_form: TimeForm | None = None
    ayanamsa_override: str | None = None
    notification_settings: dict[str, Any] | None = None


class UserOut(BaseModel):
    id: str
    email: str | None
    phone: str | None
    is_guest: bool
    display_name: str | None
    preferred_calendar_system: CalendarSystem
    language: str
    time_form: TimeForm
    ayanamsa_override: str | None
    notification_settings: dict[str, Any]

    model_config = {"from_attributes": True}


class LocationCreate(BaseModel):
    label: str
    lat: float
    lon: float
    tz: str
    dst_rule: str = "iana"
    is_favourite: bool = False
    is_travel_mode: bool = False


class LocationUpdate(BaseModel):
    label: str | None = None
    lat: float | None = None
    lon: float | None = None
    tz: str | None = None
    dst_rule: str | None = None
    is_favourite: bool | None = None
    is_travel_mode: bool | None = None


class LocationOut(BaseModel):
    id: str
    label: str
    lat: float
    lon: float
    tz: str
    dst_rule: str
    is_favourite: bool
    is_travel_mode: bool

    model_config = {"from_attributes": True}


class BirthProfileIn(BaseModel):
    """Free-form sensitive payload — encrypted whole, never partially indexed."""

    data: dict[str, Any]


class FamilyMemberIn(BaseModel):
    relation: str
    data: dict[str, Any]
