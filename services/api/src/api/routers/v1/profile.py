"""GET/PUT /v1/profile — user profile, locations, and birth vault."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_session
from api.db.v3_models import LocationRow, UserPreferenceRow, UserRow, VaultRefRow
from api.dependencies import require_auth
from api.models.auth import TokenClaims
from api.models.common import ApiResponse
from api.models.user import (
    BirthDetailsIn,
    BirthVaultRefOut,
    LocationIn,
    LocationOut,
    ProfileOut,
    ProfileUpdateIn,
)
from api.user_data import get_or_create_user
from api.vault import InMemoryVault, VaultReference

router = APIRouter(prefix="/profile", tags=["profile"])
_birth_vault = InMemoryVault()
_BIRTH_PURPOSE = "birth_details"


@router.get("", response_model=ApiResponse[ProfileOut])
async def get_profile(
    claims: Annotated[TokenClaims, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[ProfileOut]:
    user = await get_or_create_user(session, claims)
    preferences = await _get_preferences(session, user.id)
    locations = await _list_locations(session, user.id)
    return ApiResponse(data=_profile_out(user, preferences, locations))


@router.put("", response_model=ApiResponse[ProfileOut])
async def update_profile(
    body: ProfileUpdateIn,
    claims: Annotated[TokenClaims, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[ProfileOut]:
    user = await get_or_create_user(session, claims)
    preferences = await _get_preferences(session, user.id)
    if body.display_name is not None:
        user.display_name = body.display_name or None
    if body.default_ayanamsa is not None:
        preferences.ayanamsa = body.default_ayanamsa
    if body.default_month_scheme is not None:
        preferences.scheme = body.default_month_scheme
    await session.flush()
    locations = await _list_locations(session, user.id)
    return ApiResponse(data=_profile_out(user, preferences, locations))


@router.get("/locations", response_model=ApiResponse[list[LocationOut]])
async def list_locations(
    claims: Annotated[TokenClaims, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[list[LocationOut]]:
    user = await get_or_create_user(session, claims)
    return ApiResponse(data=[_location_out(row) for row in await _list_locations(session, user.id)])


@router.post(
    "/locations",
    response_model=ApiResponse[LocationOut],
    status_code=status.HTTP_201_CREATED,
)
async def add_location(
    body: LocationIn,
    claims: Annotated[TokenClaims, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[LocationOut]:
    user = await get_or_create_user(session, claims)
    if body.is_default:
        # Serialize the read-clear-insert sequence against another concurrent
        # default-location request for the same user.
        await session.execute(select(UserRow).where(UserRow.id == user.id).with_for_update())
        await _clear_primary(session, user.id)
    row = LocationRow(
        id=str(uuid.uuid4()),
        user_id=user.id,
        label=body.name,
        lat=body.lat,
        lon=body.lon,
        timezone=body.tz,
        is_primary=body.is_default,
    )
    session.add(row)
    await session.flush()
    return ApiResponse(data=_location_out(row))


@router.get("/birth-details", response_model=ApiResponse[BirthVaultRefOut])
async def get_birth_details_ref(
    claims: Annotated[TokenClaims, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[BirthVaultRefOut]:
    user = await get_or_create_user(session, claims)
    row = await _birth_ref(session, user.id)
    if row is None:
        raise HTTPException(status_code=404, detail="Birth details not found")
    return ApiResponse(data=_birth_ref_out(row))


@router.put("/birth-details", response_model=ApiResponse[BirthVaultRefOut])
async def put_birth_details(
    body: BirthDetailsIn,
    claims: Annotated[TokenClaims, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[BirthVaultRefOut]:
    user = await get_or_create_user(session, claims)
    existing = await _birth_ref(session, user.id)
    if existing is not None:
        _birth_vault.delete(
            _vault_reference(existing), actor_ref=claims.sub, purpose=_BIRTH_PURPOSE
        )
        reference_id = existing.id
    else:
        reference_id = str(uuid.uuid4())
    reference = _birth_vault.put(
        body.model_dump(mode="json", by_alias=True),
        subject_type="user",
        subject_id=user.id,
        region="default",
        purpose=_BIRTH_PURPOSE,
        reference_id=reference_id,
    )
    if existing is None:
        existing = VaultRefRow(
            id=reference.id,
            subject_type=reference.subject_type,
            subject_id=reference.subject_id,
            region=reference.region,
            purpose=reference.purpose,
            provider_ref=reference.provider_ref,
        )
        session.add(existing)
    else:
        existing.provider_ref = reference.provider_ref
    await session.flush()
    return ApiResponse(data=_birth_ref_out(existing))


@router.get("/birth-details/export", response_model=ApiResponse[BirthDetailsIn])
async def export_birth_details(
    claims: Annotated[TokenClaims, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[BirthDetailsIn]:
    user = await get_or_create_user(session, claims)
    row = await _birth_ref(session, user.id)
    if row is None:
        raise HTTPException(status_code=404, detail="Birth details not found")
    value = _birth_vault.read(
        _vault_reference(row),
        actor_ref=claims.sub,
        purpose=_BIRTH_PURPOSE,
        subject_id=user.id,
    )
    return ApiResponse(data=BirthDetailsIn.model_validate(value))


@router.delete("/birth-details", status_code=status.HTTP_204_NO_CONTENT)
async def delete_birth_details(
    claims: Annotated[TokenClaims, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    user = await get_or_create_user(session, claims)
    row = await _birth_ref(session, user.id)
    if row is not None:
        _birth_vault.delete(_vault_reference(row), actor_ref=claims.sub, purpose=_BIRTH_PURPOSE)
        await session.delete(row)
        await session.flush()


async def _get_preferences(session: AsyncSession, user_id: str) -> UserPreferenceRow:
    preferences = await session.get(UserPreferenceRow, user_id)
    if preferences is None:
        preferences = UserPreferenceRow(user_id=user_id)
        session.add(preferences)
        await session.flush()
    return preferences


async def _list_locations(session: AsyncSession, user_id: str) -> list[LocationRow]:
    return list(
        (
            await session.scalars(
                select(LocationRow)
                .where(LocationRow.user_id == user_id)
                .order_by(LocationRow.is_primary.desc(), LocationRow.created_at)
            )
        ).all()
    )


async def _clear_primary(session: AsyncSession, user_id: str) -> None:
    rows = (
        await session.scalars(
            select(LocationRow).where(
                LocationRow.user_id == user_id, LocationRow.is_primary.is_(True)
            )
        )
    ).all()
    for row in rows:
        row.is_primary = False


def _profile_out(
    user: UserRow, preferences: UserPreferenceRow, locations: list[LocationRow]
) -> ProfileOut:
    return ProfileOut(
        user_id=user.id,
        email=user.email_ref,
        display_name=user.display_name,
        default_ayanamsa=preferences.ayanamsa,
        default_month_scheme=preferences.scheme,
        locations=[_location_out(row) for row in locations],
    )


def _location_out(row: LocationRow) -> LocationOut:
    return LocationOut(
        id=row.id,
        name=row.label,
        lat=float(row.lat),
        lon=float(row.lon),
        tz=row.timezone,
        is_default=row.is_primary,
    )


async def _birth_ref(session: AsyncSession, user_id: str) -> VaultRefRow | None:
    rows = await session.scalars(
        select(VaultRefRow).where(
            VaultRefRow.subject_type == "user",
            VaultRefRow.subject_id == user_id,
            VaultRefRow.purpose == _BIRTH_PURPOSE,
        )
    )
    return rows.first()


def _vault_reference(row: VaultRefRow) -> VaultReference:
    return VaultReference(
        id=row.id,
        subject_type=row.subject_type,
        subject_id=row.subject_id,
        region=row.region,
        purpose=row.purpose,
        provider_ref=row.provider_ref,
    )


def _birth_ref_out(row: VaultRefRow) -> BirthVaultRefOut:
    return BirthVaultRefOut(
        id=row.id,
        region=row.region,
        purpose=row.purpose,
        created_at=row.created_at,
    )
