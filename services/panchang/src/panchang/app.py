"""FastAPI application — The Pandit Panchang Computation Service.

Internal service; never exposed directly to clients.
The API gateway calls this service via the configured PANCHANG_SERVICE_URL.

Routes:
  GET  /health            — liveness probe
  POST /compute           — compute a single PanchangDay
  POST /compute/month     — compute a full calendar month
  POST /warm              — trigger cache warm for a location
"""

from __future__ import annotations

from datetime import date

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from panchang.cache import PanchangCache
from panchang.compute import compute_panchang
from panchang.models import Ayanamsa, MonthScheme, PanchangRequest
from panchang.settings import get_settings

settings = get_settings()
cache = PanchangCache(compute=compute_panchang)

app = FastAPI(
    title="Panchang Computation Service",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.debug else None,
)


class ComputeRequest(BaseModel):
    date: date
    lat: float
    lon: float
    tz: str
    ayanamsa: Ayanamsa = Ayanamsa.LAHIRI
    month_scheme: MonthScheme = MonthScheme.AMANTA


class MonthRequest(BaseModel):
    year: int
    month: int
    lat: float
    lon: float
    tz: str
    ayanamsa: Ayanamsa = Ayanamsa.LAHIRI
    month_scheme: MonthScheme = MonthScheme.AMANTA


@app.get("/health", tags=["meta"], include_in_schema=False)
async def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}


@app.post("/compute")
async def compute_single(req: ComputeRequest) -> JSONResponse:
    preq = PanchangRequest(
        date=req.date,
        lat=req.lat,
        lon=req.lon,
        tz=req.tz,
        ayanamsa=req.ayanamsa,
        month_scheme=req.month_scheme,
    )
    result = cache.get(preq)
    return JSONResponse(result.model_dump(mode="json"))


@app.post("/compute/month")
async def compute_month(req: MonthRequest) -> JSONResponse:
    import calendar as _cal
    from datetime import date as _date

    days_in_month = _cal.monthrange(req.year, req.month)[1]
    results = []
    for day in range(1, days_in_month + 1):
        d = _date(req.year, req.month, day)
        preq = PanchangRequest(
            date=d,
            lat=req.lat,
            lon=req.lon,
            tz=req.tz,
            ayanamsa=req.ayanamsa,
            month_scheme=req.month_scheme,
        )
        result = cache.get(preq)
        results.append(result.model_dump(mode="json"))

    return JSONResponse({"days": results})
