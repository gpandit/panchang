"""Admin reporting routes — signups, active users, conversions."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from api.admin import analytics_store
from api.admin.rbac import AdminClaims, require_admin_role
from api.models.admin import AdminRole, ReportOut

router = APIRouter(prefix="/reporting", tags=["admin-reporting"])

_ViewerDep = Annotated[AdminClaims, Depends(require_admin_role(AdminRole.VIEWER))]

_VALID_PERIODS = {"last_7d", "last_30d", "last_90d"}


@router.get("/overview", response_model=ReportOut)
async def get_overview(claims: _ViewerDep, period: str = "last_30d") -> ReportOut:
    if period not in _VALID_PERIODS:
        raise HTTPException(
            status_code=400,
            detail=f"period must be one of {sorted(_VALID_PERIODS)}",
        )
    return analytics_store.get_report(period)
