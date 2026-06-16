"""Superuser temple management — create temples and assign admin logins.

Both endpoints require ``super_admin``. Temple admins themselves cannot create
temples or accounts; a superuser provisions them here.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from api.admin.rbac import AdminClaims, require_admin_role
from api.models.admin import AdminRole
from api.models.temple import AdminAssignIn, TempleConfig, TempleCreateIn
from api.temple import store

router = APIRouter(prefix="/temples", tags=["admin-temples"])

_SuperDep = Annotated[AdminClaims, Depends(require_admin_role(AdminRole.SUPER_ADMIN))]


@router.get("", response_model=list[TempleConfig])
async def list_temples(claims: _SuperDep) -> list[TempleConfig]:
    return store.list_temples()


@router.post("", response_model=TempleConfig, status_code=201)
async def create_temple(data: TempleCreateIn, claims: _SuperDep) -> TempleConfig:
    return store.create_temple(
        name=data.name,
        name_dev=data.name_dev,
        tagline=data.tagline,
        location=data.location,
        aarti=data.aarti,
        events=data.events,
        actor_id=claims.sub,
    )


@router.post("/{temple_id}/admins", status_code=201)
async def assign_admin(temple_id: str, data: AdminAssignIn, claims: _SuperDep) -> dict[str, str]:
    if store.get_temple(temple_id) is None:
        raise HTTPException(status_code=404, detail="Temple not found")
    account = store.assign_admin(
        email=data.email, password=data.password, temple_id=temple_id
    )
    return {"id": account.id, "email": account.email, "temple_id": account.temple_id}
