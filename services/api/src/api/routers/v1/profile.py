"""GET/PUT /v1/profile — user profile, locations, and birth vault."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import require_auth
from api.models.auth import TokenClaims
from api.models.common import ApiResponse
from api.models.user import LocationIn, LocationOut, ProfileOut, ProfileUpdateIn

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ApiResponse[ProfileOut])
async def get_profile(
    claims: Annotated[TokenClaims, Depends(require_auth)],
) -> ApiResponse[ProfileOut]:
    # TODO(step-3.4): load from Users & Profiles service
    return ApiResponse(
        data=ProfileOut(
            user_id=claims.sub,
            email=claims.email,
            display_name=None,
            default_ayanamsa="lahiri",
            default_month_scheme="amanta",
            locations=[],
        )
    )


@router.put("", response_model=ApiResponse[ProfileOut])
async def update_profile(
    body: ProfileUpdateIn,
    claims: Annotated[TokenClaims, Depends(require_auth)],
) -> ApiResponse[ProfileOut]:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not yet implemented")


@router.get("/locations", response_model=ApiResponse[list[LocationOut]])
async def list_locations(
    claims: Annotated[TokenClaims, Depends(require_auth)],
) -> ApiResponse[list[LocationOut]]:
    return ApiResponse(data=[])


@router.post("/locations", response_model=ApiResponse[LocationOut], status_code=status.HTTP_201_CREATED)
async def add_location(
    body: LocationIn,
    claims: Annotated[TokenClaims, Depends(require_auth)],
) -> ApiResponse[LocationOut]:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not yet implemented")
