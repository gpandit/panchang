"""Patron-facing marketplace router assembly — mounted at ``/v1/marketplace`` (F4).

Aggregates the stub routers from each ``api.marketplace.<module>`` package
(Architecture v1.2 §1) behind a single ``/v1/marketplace`` prefix, plus a
``healthz`` liveness check for the whole domain. Individual modules currently
expose no routes (or none beyond what's added here) — real endpoints land
progressively in WS-A/B/C/D as each workstream's steps are built.

Router registration in :mod:`api.main` stays a one-line
``app.include_router(marketplace.router, prefix=V1)`` regardless of how many
domain modules are wired in below.
"""

from __future__ import annotations

from fastapi import APIRouter

from api.marketplace.availability.router import router as availability_router
from api.marketplace.bookings.router import router as bookings_router
from api.marketplace.finance.router import router as finance_router
from api.marketplace.messaging.router import router as messaging_router
from api.marketplace.payments.router import router as payments_router
from api.marketplace.policy.router import router as policy_router
from api.marketplace.pricing.router import router as pricing_router
from api.marketplace.providers.router import router as providers_router
from api.marketplace.reviews.router import router as reviews_router
from api.marketplace.safety.router import router as safety_router
from api.marketplace.search.router import router as search_router
from api.marketplace.verification.router import router as verification_router
from api.marketplace.video.router import router as video_router

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


@router.get("/healthz")
async def marketplace_healthz() -> dict[str, str]:
    """Liveness probe for the marketplace domain — returns 200 once routers are wired."""
    return {"status": "ok"}


for _sub_router in (
    providers_router,
    verification_router,
    availability_router,
    search_router,
    bookings_router,
    pricing_router,
    payments_router,
    policy_router,
    messaging_router,
    reviews_router,
    video_router,
    safety_router,
    finance_router,
):
    router.include_router(_sub_router)

__all__ = ["router"]
