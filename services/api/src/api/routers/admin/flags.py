"""Admin flag / review queue routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from api.admin import flags_store
from api.admin.rbac import AdminClaims, require_admin_role
from api.dependencies import require_auth
from api.models.admin import AdminRole, FlagIn, FlagRecord, FlagResolve, FlagStatus
from api.models.auth import TokenClaims

router = APIRouter(prefix="/flags", tags=["admin-flags"])

_ViewerDep = Annotated[AdminClaims, Depends(require_admin_role(AdminRole.VIEWER))]
_EditorDep = Annotated[AdminClaims, Depends(require_admin_role(AdminRole.EDITOR))]
_AuthDep = Annotated[TokenClaims, Depends(require_auth)]


@router.post("/report", response_model=FlagRecord, status_code=201)
async def report_flag(data: FlagIn, claims: _AuthDep) -> FlagRecord:
    """Any authenticated user can flag content or a Panchang date."""
    return flags_store.create_flag(data, reported_by=claims.sub)


@router.get("", response_model=list[FlagRecord])
async def list_flags(
    claims: _ViewerDep,
    status_filter: str | None = None,
) -> list[FlagRecord]:
    st = FlagStatus(status_filter) if status_filter else None
    return flags_store.list_flags(status=st)


@router.get("/{flag_id}", response_model=FlagRecord)
async def get_flag(flag_id: str, claims: _ViewerDep) -> FlagRecord:
    flag = flags_store.get_flag(flag_id)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    return flag


@router.post("/{flag_id}/resolve", response_model=FlagRecord)
async def resolve_flag(flag_id: str, body: FlagResolve, claims: _EditorDep) -> FlagRecord:
    flag = flags_store.get_flag(flag_id)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    if flag.status not in (FlagStatus.OPEN, FlagStatus.IN_REVIEW):
        raise HTTPException(
            status_code=400,
            detail=f"Flag is already '{flag.status}' and cannot be actioned again.",
        )
    if body.action not in ("resolve", "dismiss"):
        raise HTTPException(status_code=400, detail="action must be 'resolve' or 'dismiss'")
    return flags_store.resolve_flag(
        flag_id,
        action=body.action,
        resolution_note=body.resolution_note,
        actor_id=claims.sub,
        actor_email=claims.email,
    )
