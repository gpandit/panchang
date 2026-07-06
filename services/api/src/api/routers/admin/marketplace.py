"""Admin-facing marketplace router — mounted at ``/admin/v1/marketplace`` (F4).

Scaffolding only: the marketplace admin consoles (provider approval queue,
taxonomy management, commission config, booking/dispute console, payout
reconciliation, moderation/fraud dashboards) are **WS-E** (E1-E6) and are not
built here. This module exists so the ``/admin/v1`` prefix has a marketplace
namespace to register real RBAC-gated routes against as each WS-E step lands
(same pattern as ``api.routers.admin.temples`` / ``.flags`` / ``.content``).
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/marketplace", tags=["admin-marketplace"])


@router.get("/healthz")
async def admin_marketplace_healthz() -> dict[str, str]:
    """Liveness probe for the marketplace admin namespace."""
    return {"status": "ok"}
