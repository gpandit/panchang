"""GET /v1/festivals — festival/vrat listing from the CMS.
GET /v1/festivals/{festival_id} — full festival detail (body, puja, katha).

Only published CMS entries are returned by the public API.
Region and locale query parameters filter the result set.
"""

from __future__ import annotations

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from api.cms.store import get_festival, list_festivals
from api.dependencies import require_auth
from api.models.auth import TokenClaims
from api.models.common import ApiResponse, PaginatedMeta, PaginatedResponse
from api.models.content import FestivalDetailOut, FestivalOut

router = APIRouter(prefix="/festivals", tags=["festivals"])


def _to_festival_out(f: object) -> FestivalOut:
    from api.cms.store import FestivalContent

    assert isinstance(f, FestivalContent)
    return FestivalOut(
        id=f.id,
        name=f.name,
        date=f.date,
        description=f.description,
        tags=f.tags,
        region=f.region,
        locale=f.locale,
    )


def _to_detail_out(f: object) -> FestivalDetailOut:
    from api.cms.store import FestivalContent

    assert isinstance(f, FestivalContent)
    return FestivalDetailOut(
        id=f.id,
        name=f.name,
        date=f.date,
        description=f.description,
        tags=f.tags,
        region=f.region,
        locale=f.locale,
        body=f.body,
        puja=f.puja,
        katha=f.katha,
    )


@router.get(
    "",
    response_model=PaginatedResponse[FestivalOut],
    summary="List festivals",
)
async def list_festivals_endpoint(
    year: Annotated[int, Query(ge=1900, le=2200)] = datetime.date.today().year,
    month: Annotated[int | None, Query(ge=1, le=12)] = None,
    region: Annotated[str | None, Query(max_length=32)] = None,
    locale: Annotated[str | None, Query(max_length=10)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    _claims: Annotated[TokenClaims, Depends(require_auth)] = ...,  # type: ignore[assignment]
) -> PaginatedResponse[FestivalOut]:
    _ = year  # date-based filtering wired in step 3.5 when rule engine is ready
    _ = month
    items = list_festivals(region=region, locale=locale, published_only=True)
    total = len(items)
    start = (page - 1) * page_size
    page_items = items[start : start + page_size]
    return PaginatedResponse(
        data=[_to_festival_out(f) for f in page_items],
        meta=PaginatedMeta(
            total=total,
            page=page,
            page_size=page_size,
            has_next=start + page_size < total,
        ),
    )


@router.get(
    "/{festival_id}",
    response_model=ApiResponse[FestivalDetailOut],
    summary="Get festival detail",
)
async def get_festival_endpoint(
    festival_id: Annotated[str, Path(max_length=128)],
    _claims: Annotated[TokenClaims, Depends(require_auth)] = ...,  # type: ignore[assignment]
) -> ApiResponse[FestivalDetailOut]:
    festival = get_festival(festival_id, published_only=True)
    if festival is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Festival not found")
    return ApiResponse(data=_to_detail_out(festival))
