"""Persistent authenticated bookmarks."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_session
from api.db.v3_models import BookmarkRow
from api.dependencies import require_auth
from api.models.auth import TokenClaims
from api.models.common import ApiResponse
from api.models.content import BookmarkIn, BookmarkOut
from api.user_data import count_owned, get_or_create_user, owned_filter

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])


@router.get("", response_model=ApiResponse[list[BookmarkOut]])
async def list_bookmarks(
    claims: Annotated[TokenClaims, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[list[BookmarkOut]]:
    user = await get_or_create_user(session, claims)
    rows = (
        await session.scalars(
            select(BookmarkRow)
            .where(owned_filter(BookmarkRow, user.id))
            .order_by(BookmarkRow.created_at)
        )
    ).all()
    return ApiResponse(data=[_out(row) for row in rows])


@router.post("", response_model=ApiResponse[BookmarkOut], status_code=status.HTTP_201_CREATED)
async def create_bookmark(
    body: BookmarkIn,
    claims: Annotated[TokenClaims, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[BookmarkOut]:
    user = await get_or_create_user(session, claims)
    existing = await session.scalar(
        select(BookmarkRow).where(
            owned_filter(BookmarkRow, user.id),
            BookmarkRow.target_type == body.target_type,
            BookmarkRow.target_id == body.target_id,
            BookmarkRow.category == body.category,
        )
    )
    if existing is not None:
        return ApiResponse(data=_out(existing))
    if claims.tier.value == "basic" and await count_owned(session, BookmarkRow, user.id) >= 5:
        raise HTTPException(
            status_code=403, detail={"code": "quota_exceeded", "resource": "bookmarks"}
        )
    row = BookmarkRow(
        id=str(uuid.uuid4()),
        user_id=user.id,
        target_type=body.target_type,
        target_id=body.target_id,
        category=body.category,
    )
    session.add(row)
    await session.flush()
    return ApiResponse(data=_out(row))


@router.get("/{bookmark_id}", response_model=ApiResponse[BookmarkOut])
async def get_bookmark(
    bookmark_id: Annotated[str, Path()],
    claims: Annotated[TokenClaims, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[BookmarkOut]:
    user = await get_or_create_user(session, claims)
    row = await session.scalar(
        select(BookmarkRow).where(BookmarkRow.id == bookmark_id, owned_filter(BookmarkRow, user.id))
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return ApiResponse(data=_out(row))


@router.delete("/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookmark(
    bookmark_id: Annotated[str, Path()],
    claims: Annotated[TokenClaims, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    user = await get_or_create_user(session, claims)
    row = await session.scalar(
        select(BookmarkRow).where(BookmarkRow.id == bookmark_id, owned_filter(BookmarkRow, user.id))
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    await session.delete(row)


def _out(row: BookmarkRow) -> BookmarkOut:
    return BookmarkOut(
        id=row.id,
        target_type=row.target_type,
        target_id=row.target_id,
        category=row.category,
        created_at=row.created_at,
    )
