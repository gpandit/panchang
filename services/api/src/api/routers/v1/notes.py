"""CRUD /v1/notes — user notes anchored to Panchang days."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from api.dependencies import require_auth
from api.models.auth import TokenClaims
from api.models.common import ApiResponse
from api.models.content import NoteIn, NoteOut

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("", response_model=ApiResponse[list[NoteOut]])
async def list_notes(
    claims: Annotated[TokenClaims, Depends(require_auth)],
) -> ApiResponse[list[NoteOut]]:
    # TODO(step-3.3): query user notes from DB
    return ApiResponse(data=[])


@router.post("", response_model=ApiResponse[NoteOut], status_code=status.HTTP_201_CREATED)
async def create_note(
    body: NoteIn,
    claims: Annotated[TokenClaims, Depends(require_auth)],
) -> ApiResponse[NoteOut]:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not yet implemented")


@router.get("/{note_id}", response_model=ApiResponse[NoteOut])
async def get_note(
    note_id: Annotated[str, Path()],
    claims: Annotated[TokenClaims, Depends(require_auth)],
) -> ApiResponse[NoteOut]:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")


@router.put("/{note_id}", response_model=ApiResponse[NoteOut])
async def update_note(
    note_id: Annotated[str, Path()],
    body: NoteIn,
    claims: Annotated[TokenClaims, Depends(require_auth)],
) -> ApiResponse[NoteOut]:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: Annotated[str, Path()],
    claims: Annotated[TokenClaims, Depends(require_auth)],
) -> None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
