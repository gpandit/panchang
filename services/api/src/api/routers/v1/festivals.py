"""GET /v1/festivals — festival/vrat listing.

Requires authentication. Gold tier unlocks extended content fields.
"""

from __future__ import annotations

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from api.dependencies import require_auth
from api.models.auth import TokenClaims
from api.models.common import ApiResponse, PaginatedMeta, PaginatedResponse
from api.models.content import FestivalOut

router = APIRouter(prefix="/festivals", tags=["festivals"])


@router.get(
    "",
    response_model=PaginatedResponse[FestivalOut],
    summary="List festivals",
)
async def list_festivals(
    year: Annotated[int, Query(ge=1900, le=2200)] = datetime.date.today().year,
    month: Annotated[int | None, Query(ge=1, le=12)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    _claims: Annotated[TokenClaims, Depends(require_auth)] = ...,
) -> PaginatedResponse[FestivalOut]:
    # TODO(step-3.2): query the Festival & Vrat Rules service
    items: list[FestivalOut] = []
    return PaginatedResponse(
        data=items,
        meta=PaginatedMeta(total=0, page=page, page_size=page_size, has_next=False),
    )
