"""CRUD /v1/notes — user notes anchored to Panchang days."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_session
from api.db.v3_models import NoteRow
from api.dependencies import require_auth
from api.models.auth import TokenClaims
from api.models.common import ApiResponse
from api.models.content import NoteIn, NoteOut
from api.user_data import count_owned, get_or_create_user, owned_filter

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("", response_model=ApiResponse[list[NoteOut]])
async def list_notes(
    claims: Annotated[TokenClaims, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[list[NoteOut]]:
    user = await get_or_create_user(session, claims)
    rows = (
        await session.scalars(
            select(NoteRow)
            .where(owned_filter(NoteRow, user.id))
            .order_by(NoteRow.date_ref, NoteRow.created_at)
        )
    ).all()
    return ApiResponse(data=[_out(row) for row in rows])


@router.post("", response_model=ApiResponse[NoteOut], status_code=status.HTTP_201_CREATED)
async def create_note(
    body: NoteIn,
    claims: Annotated[TokenClaims, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[NoteOut]:
    user = await get_or_create_user(session, claims)
    if claims.tier.value == "basic" and await count_owned(session, NoteRow, user.id) >= 5:
        raise HTTPException(status_code=403, detail={"code": "quota_exceeded", "resource": "notes"})
    row = NoteRow(
        id=str(uuid.uuid4()),
        owner_user_id=user.id,
        date_ref=date.fromisoformat(body.date),
        category="calendar",
        body=body.body,
        tags=body.tags,
    )
    session.add(row)
    await session.flush()
    return ApiResponse(data=_out(row))


@router.get("/{note_id}", response_model=ApiResponse[NoteOut])
async def get_note(
    note_id: Annotated[str, Path()],
    claims: Annotated[TokenClaims, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[NoteOut]:
    user = await get_or_create_user(session, claims)
    row = await session.scalar(
        select(NoteRow).where(NoteRow.id == note_id, owned_filter(NoteRow, user.id))
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return ApiResponse(data=_out(row))


@router.put("/{note_id}", response_model=ApiResponse[NoteOut])
async def update_note(
    note_id: Annotated[str, Path()],
    body: NoteIn,
    claims: Annotated[TokenClaims, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[NoteOut]:
    user = await get_or_create_user(session, claims)
    row = await session.scalar(
        select(NoteRow).where(NoteRow.id == note_id, owned_filter(NoteRow, user.id))
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    row.date_ref = date.fromisoformat(body.date)
    row.body = body.body
    row.tags = body.tags
    row.version += 1
    await session.flush()
    return ApiResponse(data=_out(row))


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: Annotated[str, Path()],
    claims: Annotated[TokenClaims, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    user = await get_or_create_user(session, claims)
    row = await session.scalar(
        select(NoteRow).where(NoteRow.id == note_id, owned_filter(NoteRow, user.id))
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    await session.delete(row)


def _out(row: NoteRow) -> NoteOut:
    return NoteOut(
        id=row.id,
        date=row.date_ref.isoformat() if row.date_ref else "",
        body=row.body,
        tags=list(row.tags or []),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
