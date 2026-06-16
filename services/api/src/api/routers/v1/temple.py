"""GET /v1/temple/{temple_id} — public, read-only temple config for the Display.

The Temple Display screen is a public signage surface, so this endpoint requires no
auth (mirrors public published-festival reads). It returns the same ``TempleConfig``
the temple admin edits.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.models.temple import TempleConfig
from api.temple import store

router = APIRouter(prefix="/temple", tags=["temple"])


@router.get("/{temple_id}", response_model=TempleConfig)
async def get_temple(temple_id: str) -> TempleConfig:
    temple = store.get_temple(temple_id)
    if temple is None:
        raise HTTPException(status_code=404, detail="Temple not found")
    return temple
