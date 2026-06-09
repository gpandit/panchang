"""Admin content management routes — CRUD + draft/review/publish workflow."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.admin import audit as audit_log
from api.admin import content_store
from api.admin.rbac import AdminClaims, require_admin_role
from api.models.admin import AdminRole, ContentStatus, FestivalIn, FestivalRecord

router = APIRouter(prefix="/content", tags=["admin-content"])

_EditorDep = Annotated[AdminClaims, Depends(require_admin_role(AdminRole.EDITOR))]
_PublisherDep = Annotated[AdminClaims, Depends(require_admin_role(AdminRole.PUBLISHER))]
_ViewerDep = Annotated[AdminClaims, Depends(require_admin_role(AdminRole.VIEWER))]


@router.get("/festivals", response_model=list[FestivalRecord])
async def list_festivals(
    claims: _ViewerDep,
    status_filter: str | None = None,
) -> list[FestivalRecord]:
    st = ContentStatus(status_filter) if status_filter else None
    return content_store.list_records(status=st)


@router.get("/festivals/{festival_id}", response_model=FestivalRecord)
async def get_festival(festival_id: str, claims: _ViewerDep) -> FestivalRecord:
    record = content_store.get_record(festival_id)
    if not record:
        raise HTTPException(status_code=404, detail="Festival not found")
    return record


@router.post("/festivals", response_model=FestivalRecord, status_code=201)
async def create_festival(data: FestivalIn, claims: _EditorDep) -> FestivalRecord:
    return content_store.create_record(data, actor_id=claims.sub, actor_email=claims.email)


@router.put("/festivals/{festival_id}", response_model=FestivalRecord)
async def update_festival(
    festival_id: str,
    data: FestivalIn,
    claims: _EditorDep,
) -> FestivalRecord:
    if not content_store.get_record(festival_id):
        raise HTTPException(status_code=404, detail="Festival not found")
    return content_store.update_record(
        festival_id, data, actor_id=claims.sub, actor_email=claims.email
    )


@router.post("/festivals/{festival_id}/submit-review", response_model=FestivalRecord)
async def submit_for_review(festival_id: str, claims: _EditorDep) -> FestivalRecord:
    record = content_store.get_record(festival_id)
    if not record:
        raise HTTPException(status_code=404, detail="Festival not found")
    if record.status not in (ContentStatus.DRAFT, ContentStatus.REJECTED):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot submit for review from status '{record.status}'",
        )
    return content_store.transition_status(
        festival_id,
        ContentStatus.REVIEW,
        actor_id=claims.sub,
        actor_email=claims.email,
    )


@router.post("/festivals/{festival_id}/publish", response_model=FestivalRecord)
async def publish_festival(festival_id: str, claims: _PublisherDep) -> FestivalRecord:
    record = content_store.get_record(festival_id)
    if not record:
        raise HTTPException(status_code=404, detail="Festival not found")
    if record.status != ContentStatus.REVIEW:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot publish from status '{record.status}' — must be in 'review'",
        )
    return content_store.transition_status(
        festival_id,
        ContentStatus.PUBLISHED,
        actor_id=claims.sub,
        actor_email=claims.email,
    )


@router.post("/festivals/{festival_id}/reject", response_model=FestivalRecord)
async def reject_festival(festival_id: str, claims: _PublisherDep) -> FestivalRecord:
    record = content_store.get_record(festival_id)
    if not record:
        raise HTTPException(status_code=404, detail="Festival not found")
    if record.status != ContentStatus.REVIEW:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject from status '{record.status}'",
        )
    return content_store.transition_status(
        festival_id,
        ContentStatus.REJECTED,
        actor_id=claims.sub,
        actor_email=claims.email,
    )


@router.delete("/festivals/{festival_id}", status_code=204)
async def delete_festival(festival_id: str, claims: _PublisherDep) -> None:
    if not content_store.get_record(festival_id):
        raise HTTPException(status_code=404, detail="Festival not found")
    content_store.delete_record(festival_id, actor_id=claims.sub, actor_email=claims.email)


@router.get("/audit", response_model=list)
async def get_audit_trail(
    claims: _ViewerDep,
    resource_type: str | None = None,
    resource_id: str | None = None,
    limit: int = 100,
) -> list:
    return audit_log.list_entries(
        resource_type=resource_type,
        resource_id=resource_id,
        limit=limit,
    )
