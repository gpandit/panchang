"""GET /v1/panchang/daily  — daily Panchang (authenticated, location-keyed, cached).
GET /v1/panchang/month   — calendar-month view (Silver+, burst-rate-limited).

Edge caching:
  - Daily:  Cache-Control: public, max-age=3600, s-maxage=3600
            Surrogate-Key: panchang daily {date}
  - Month:  Cache-Control: public, max-age=1800, s-maxage=1800
            Surrogate-Key: panchang month {year}-{month}
"""

from __future__ import annotations

import calendar
import datetime
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from api.dependencies import require_auth, require_tier
from api.models.auth import SubscriptionTier, TokenClaims
from api.models.common import ApiResponse
from api.models.panchang import DailyPanchangOut, MonthCalendarOut
from api.panchang_client import fetch_daily_panchang

router = APIRouter(prefix="/panchang", tags=["panchang"])


@router.get(
    "/daily",
    response_model=ApiResponse[DailyPanchangOut],
    summary="Daily Panchang",
    description=(
        "Returns the full Panchang for the requested date and location. "
        "Served from the edge/in-process cache — typical p99 < 50 ms on cache hit."
    ),
)
async def daily_panchang(
    response: Response,
    date: Annotated[datetime.date, Query(description="Gregorian date (YYYY-MM-DD)")],
    lat: Annotated[float, Query(ge=-90, le=90, description="Latitude")],
    lon: Annotated[float, Query(ge=-180, le=180, description="Longitude")],
    tz: Annotated[str, Query(description="IANA timezone, e.g. Asia/Kolkata")],
    ayanamsa: Annotated[str, Query(description="Ayanamsa (lahiri)")] = "lahiri",
    month_scheme: Annotated[str, Query(description="amanta or purnimanta")] = "amanta",
    _claims: Annotated[TokenClaims, Depends(require_auth)] = ...,  # type: ignore[assignment]
) -> ApiResponse[DailyPanchangOut]:
    try:
        result = await fetch_daily_panchang(
            date=date.isoformat(),
            lat=lat,
            lon=lon,
            tz=tz,
            ayanamsa=ayanamsa,
            month_scheme=month_scheme,
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Panchang service error: {exc.response.status_code}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Panchang service unreachable: {exc}",
        ) from exc

    # Edge caching headers — CDN caches for 1 hour, respects Surrogate-Key purge
    response.headers["Cache-Control"] = "public, max-age=3600, s-maxage=3600"
    response.headers["Surrogate-Key"] = f"panchang daily {date.isoformat()}"
    if result.cached:
        response.headers["X-Cache"] = "HIT"
    else:
        response.headers["X-Cache"] = "MISS"

    return ApiResponse(data=result)


@router.get(
    "/month",
    response_model=ApiResponse[MonthCalendarOut],
    summary="Monthly Panchang calendar (Silver+)",
    description="Returns Panchang for every day in the requested month. Requires Silver tier.",
)
async def month_calendar(
    response: Response,
    year: Annotated[int, Query(ge=1900, le=2200)],
    month: Annotated[int, Query(ge=1, le=12)],
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    tz: Annotated[str, Query()],
    ayanamsa: str = "lahiri",
    month_scheme: str = "amanta",
    _claims: Annotated[TokenClaims, Depends(require_tier(SubscriptionTier.SILVER))] = ...,  # type: ignore[assignment]
) -> ApiResponse[MonthCalendarOut]:
    # Mark as burst so rate limiter applies the tighter limit
    response.headers["X-Rate-Limit-Tier"] = "burst"

    _, days_in_month = calendar.monthrange(year, month)
    day_results: list[DailyPanchangOut] = []

    for day in range(1, days_in_month + 1):
        d = datetime.date(year, month, day)
        try:
            result = await fetch_daily_panchang(
                date=d.isoformat(),
                lat=lat,
                lon=lon,
                tz=tz,
                ayanamsa=ayanamsa,
                month_scheme=month_scheme,
            )
            day_results.append(result)
        except (httpx.HTTPStatusError, httpx.RequestError):
            # Partial data: skip failing days rather than aborting the whole month
            continue

    response.headers["Cache-Control"] = "public, max-age=1800, s-maxage=1800"
    response.headers["Surrogate-Key"] = f"panchang month {year}-{month:02d}"

    return ApiResponse(data=MonthCalendarOut(year=year, month=month, days=day_results))
