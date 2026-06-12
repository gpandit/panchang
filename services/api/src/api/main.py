"""FastAPI application — The Pandit API Gateway.

Versioned REST/JSON surface. All clients (web, iOS, Android, admin) call
this service exclusively; domain services are never exposed directly.

Version prefix: /v1/...
OpenAPI schema:  GET /openapi.json  (also /docs and /redoc in debug mode)
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.middleware.rate_limit import SlidingWindowRateLimiter
from api.models.common import ApiError, ApiErrorResponse
from api.routers.admin import content as admin_content
from api.routers.admin import flags as admin_flags
from api.routers.admin import reporting as admin_reporting
from api.routers.v1 import (
    festivals,
    notes,
    panchang,
    pdf,
    profile,
    reminders,
    subscriptions,
)
from api.settings import get_settings

settings = get_settings()

app = FastAPI(
    title="The Pandit API",
    version="1.0.0",
    description=(
        "Versioned REST/JSON gateway for The Pandit platform. "
        "Clients (web, iOS, Android, admin) call this service exclusively — "
        "domain services are never exposed directly.\n\n"
        "**Auth:** Bearer JWT in the Authorization header.\n\n"
        "**Tiers:** basic < silver < gold. "
        "Gated endpoints return 403 when the caller's tier is insufficient."
    ),
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Tightened to specific origins in staging/prod via the allowed_origins setting.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate limiting ─────────────────────────────────────────────────────────────
app.add_middleware(
    SlidingWindowRateLimiter,
    requests_per_minute=settings.rate_limit_per_minute,
    burst_per_minute=settings.rate_limit_burst_per_minute,
)

# ── v1 routers ────────────────────────────────────────────────────────────────
V1 = "/v1"

app.include_router(panchang.router, prefix=V1)
app.include_router(festivals.router, prefix=V1)
app.include_router(notes.router, prefix=V1)
app.include_router(reminders.router, prefix=V1)
app.include_router(profile.router, prefix=V1)
app.include_router(subscriptions.router, prefix=V1)
app.include_router(pdf.router, prefix=V1)

# ── Admin routers ─────────────────────────────────────────────────────────────
ADMIN = "/admin/v1"

app.include_router(admin_content.router, prefix=ADMIN)
app.include_router(admin_flags.router, prefix=ADMIN)
app.include_router(admin_reporting.router, prefix=ADMIN)


# ── Global exception handlers ─────────────────────────────────────────────────


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=ApiErrorResponse(
            error=ApiError(code="not_found", message="The requested resource was not found.")
        ).model_dump(),
    )


@app.exception_handler(405)
async def method_not_allowed_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=405,
        content=ApiErrorResponse(
            error=ApiError(code="method_not_allowed", message="Method not allowed.")
        ).model_dump(),
    )


# ── Health / meta ─────────────────────────────────────────────────────────────


@app.get("/health", tags=["meta"], include_in_schema=False)
async def health_check() -> dict[str, str]:
    """Liveness probe — returns 200 if the process is alive."""
    return {"status": "ok", "environment": settings.environment}
