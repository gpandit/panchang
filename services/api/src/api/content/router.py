"""FastAPI router for the Content / CMS module.

Public routes   → /v1/content/*      (published items only)
Admin routes    → /v1/admin/content/* (full editorial surface)

Dependency injection: `get_content_service` is overridden in `main.py`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.content.schemas import (
    ContentCreateRequest,
    ContentItemAdminOut,
    ContentItemPublicOut,
    ContentUpdateRequest,
    FlagOut,
    FlagRequest,
)
from api.content.service import ContentError, ContentService

# ── Dependency stub (overridden in main.py) ───────────────────────────────────


async def get_content_service() -> ContentService:  # pragma: no cover
    raise NotImplementedError("get_content_service dependency must be overridden")


router = APIRouter(tags=["content"])


# ── Public API ────────────────────────────────────────────────────────────────


@router.get("/v1/content", response_model=list[ContentItemPublicOut])
async def list_published_content(
    svc: Annotated[ContentService, Depends(get_content_service)],
    locale: str | None = Query(None, description="BCP-47 locale, e.g. 'hi', 'en'"),
    region_tag: str | None = Query(None, description="Region tag, e.g. 'north', 'gujarat'"),
    content_type: str | None = Query(
        None, description="festival | vrat | educational | mantra | template"
    ),
    festival_rule_id: str | None = Query(None),
) -> list[ContentItemPublicOut]:
    pairs = await svc.get_published(
        locale=locale,
        region_tag=region_tag,
        content_type=content_type,
        festival_rule_id=festival_rule_id,
    )
    return [_to_public(item, ver) for item, ver in pairs]


@router.get("/v1/content/{slug}", response_model=ContentItemPublicOut)
async def get_published_content(
    slug: str,
    svc: Annotated[ContentService, Depends(get_content_service)],
    locale: str | None = Query(None),
) -> ContentItemPublicOut:
    try:
        item, ver = await svc.get_published_one(slug=slug, locale=locale)
    except ContentError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_public(item, ver)


@router.post(
    "/v1/content/{item_id}/flag", response_model=FlagOut, status_code=status.HTTP_201_CREATED
)
async def flag_content(
    item_id: str,
    req: FlagRequest,
    svc: Annotated[ContentService, Depends(get_content_service)],
) -> FlagOut:
    try:
        flag = await svc.flag(item_id, req)
    except ContentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return FlagOut.model_validate(flag)


# ── Admin API ─────────────────────────────────────────────────────────────────


@router.post(
    "/v1/admin/content", response_model=ContentItemAdminOut, status_code=status.HTTP_201_CREATED
)
async def create_content(
    req: ContentCreateRequest,
    svc: Annotated[ContentService, Depends(get_content_service)],
) -> ContentItemAdminOut:
    item = await svc.create_draft(req)
    item = await svc.get_item(item.id)
    return ContentItemAdminOut.model_validate(item)


@router.put("/v1/admin/content/{item_id}", response_model=ContentItemAdminOut)
async def update_content(
    item_id: str,
    req: ContentUpdateRequest,
    svc: Annotated[ContentService, Depends(get_content_service)],
) -> ContentItemAdminOut:
    try:
        await svc.update_draft(item_id, req)
        item = await svc.get_item(item_id)
    except ContentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ContentItemAdminOut.model_validate(item)


@router.get("/v1/admin/content", response_model=list[ContentItemAdminOut])
async def list_all_content(
    svc: Annotated[ContentService, Depends(get_content_service)],
    status_filter: str | None = Query(None, alias="status"),
    content_type: str | None = Query(None),
    locale: str | None = Query(None),
) -> list[ContentItemAdminOut]:
    items = await svc.list_items(status=status_filter, content_type=content_type, locale=locale)
    return [ContentItemAdminOut.model_validate(i) for i in items]


@router.get("/v1/admin/content/{item_id}", response_model=ContentItemAdminOut)
async def get_content_item(
    item_id: str,
    svc: Annotated[ContentService, Depends(get_content_service)],
) -> ContentItemAdminOut:
    try:
        item = await svc.get_item(item_id)
    except ContentError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ContentItemAdminOut.model_validate(item)


@router.post("/v1/admin/content/{item_id}/review", response_model=ContentItemAdminOut)
async def submit_for_review(
    item_id: str,
    svc: Annotated[ContentService, Depends(get_content_service)],
) -> ContentItemAdminOut:
    try:
        await svc.submit_for_review(item_id)
        item = await svc.get_item(item_id)
    except ContentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ContentItemAdminOut.model_validate(item)


@router.post("/v1/admin/content/{item_id}/publish", response_model=ContentItemAdminOut)
async def publish_content(
    item_id: str,
    svc: Annotated[ContentService, Depends(get_content_service)],
) -> ContentItemAdminOut:
    try:
        await svc.publish(item_id)
        item = await svc.get_item(item_id)
    except ContentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ContentItemAdminOut.model_validate(item)


@router.post("/v1/admin/content/{item_id}/archive", response_model=ContentItemAdminOut)
async def archive_content(
    item_id: str,
    svc: Annotated[ContentService, Depends(get_content_service)],
) -> ContentItemAdminOut:
    try:
        await svc.archive(item_id)
        item = await svc.get_item(item_id)
    except ContentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ContentItemAdminOut.model_validate(item)


@router.get("/v1/admin/content/{item_id}/flags", response_model=list[FlagOut])
async def get_flags(
    item_id: str,
    svc: Annotated[ContentService, Depends(get_content_service)],
) -> list[FlagOut]:
    flags = await svc.list_flags(item_id)
    return [FlagOut.model_validate(f) for f in flags]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _to_public(item, ver) -> ContentItemPublicOut:
    return ContentItemPublicOut(
        id=item.id,
        slug=item.slug,
        content_type=item.content_type,
        locale=item.locale,
        region_tags=item.region_tags or [],
        festival_rule_id=item.festival_rule_id,
        published_version=item.published_version,
        body=ver.body,
        source_attribution=ver.source_attribution,
        published_at=ver.published_at,
    )
