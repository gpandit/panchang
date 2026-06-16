"""Temple-admin config management — read/update the caller's assigned temple.

The ``temple_id`` is always taken from the JWT, never the request body, so an admin
can only ever read or modify the temple a superuser bound them to.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from api.models.temple import TempleConfig, TempleConfigIn
from api.temple import store
from api.temple.rbac import TempleClaims, require_temple_admin

router = APIRouter(prefix="/temple", tags=["temple-config"])

_TempleDep = Annotated[TempleClaims, Depends(require_temple_admin)]


@router.get("", response_model=TempleConfig)
async def get_my_temple(claims: _TempleDep) -> TempleConfig:
    temple = store.get_temple(claims.temple_id)
    if temple is None:
        raise HTTPException(status_code=404, detail="Assigned temple not found")
    return temple


@router.put("", response_model=TempleConfig)
async def update_my_temple(data: TempleConfigIn, claims: _TempleDep) -> TempleConfig:
    updated = store.update_temple(claims.temple_id, data, actor_id=claims.sub)
    if updated is None:
        raise HTTPException(status_code=404, detail="Assigned temple not found")
    return updated
