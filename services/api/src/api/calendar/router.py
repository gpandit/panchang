"""Calendar Assembly API routes — Step 2.4."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from api.calendar.schemas import (
    DayCell,
    LocationParams,
    MonthView,
    RangeView,
    WeekView,
    YearView,
)
from api.calendar.service import CalendarService

router = APIRouter(prefix="/v1/calendar", tags=["calendar"])


def get_calendar_service() -> CalendarService:  # pragma: no cover
    """Overridden in main.py with the real wired service."""
    raise NotImplementedError


def _loc(
    lat: float = Query(..., description="Latitude (-90 to 90)"),
    lon: float = Query(..., description="Longitude (-180 to 180)"),
    tz: str = Query(..., description="IANA timezone, e.g. Asia/Kolkata"),
    ayanamsa: str = Query("lahiri", description="Ayanamsa — only 'lahiri' supported"),
    month_scheme: str = Query(
        "amanta", description="Month scheme: 'amanta' or 'purnimanta'"
    ),
    region_tags: list[str] = Query(default=[], description="Optional regional variant tags"),
) -> LocationParams:
    if ayanamsa not in ("lahiri",):
        raise HTTPException(422, f"Unsupported ayanamsa: {ayanamsa!r}")
    if month_scheme not in ("amanta", "purnimanta"):
        raise HTTPException(422, f"Unsupported month_scheme: {month_scheme!r}")
    return LocationParams(
        lat=lat,
        lon=lon,
        tz=tz,
        ayanamsa=ayanamsa,
        month_scheme=month_scheme,
        region_tags=region_tags,
    )


@router.get("/day", response_model=DayCell)
def get_day(
    date_: date = Query(..., alias="date", description="Gregorian date (YYYY-MM-DD)"),
    loc: LocationParams = Depends(_loc),
    svc: CalendarService = Depends(get_calendar_service),
) -> DayCell:
    """Return a fully assembled day cell for the given date and location."""
    return svc.day(date_, loc)


@router.get("/week", response_model=WeekView)
def get_week(
    date_: date = Query(
        ..., alias="date", description="Any date within the target week"
    ),
    loc: LocationParams = Depends(_loc),
    svc: CalendarService = Depends(get_calendar_service),
) -> WeekView:
    """Return the Mon–Sun week containing `date`."""
    return svc.week(date_, loc)


@router.get("/month", response_model=MonthView)
def get_month(
    year: int = Query(..., ge=1800, le=2200),
    month: int = Query(..., ge=1, le=12),
    loc: LocationParams = Depends(_loc),
    svc: CalendarService = Depends(get_calendar_service),
) -> MonthView:
    """Return the full Gregorian calendar month."""
    return svc.month(year, month, loc)


@router.get("/year", response_model=YearView)
def get_year(
    year: int = Query(..., ge=1800, le=2200),
    loc: LocationParams = Depends(_loc),
    svc: CalendarService = Depends(get_calendar_service),
) -> YearView:
    """Return all 12 months of a Gregorian year."""
    return svc.year(year, loc)


@router.get("/range", response_model=RangeView)
def get_range(
    start: date = Query(..., description="Range start date (inclusive)"),
    end: date = Query(..., description="Range end date (inclusive)"),
    loc: LocationParams = Depends(_loc),
    svc: CalendarService = Depends(get_calendar_service),
) -> RangeView:
    """Return a continuous range (up to 550 days / ~18 months) for infinite scroll."""
    if end < start:
        raise HTTPException(422, "end must be >= start")
    try:
        return svc.range(start, end, loc)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
