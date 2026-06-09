"""HTTP routes for the Users module — thin wrappers over `UserService`.

Wiring `get_user_service` to a real session/secret-key/vault is the
responsibility of `api.main` (Stage 3 gateway assembly); this router only
defines the surface and depends on it via FastAPI `Depends`.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.users.schemas import (
    BirthProfileIn,
    FamilyMemberIn,
    LocationCreate,
    LocationOut,
    LocationUpdate,
    LoginWithPassword,
    PreferencesUpdate,
    RefreshRequest,
    SignUpWithOAuth,
    SignUpWithPassword,
    TokenPairOut,
    UserOut,
)
from api.users.service import AuthError, NotFoundError, UserService

router = APIRouter(prefix="/users", tags=["users"])
_bearer = HTTPBearer(auto_error=False)


def get_user_service() -> UserService:  # pragma: no cover - overridden in app wiring/tests
    raise NotImplementedError("get_user_service must be overridden via dependency_overrides")


def get_secret_key() -> str:  # pragma: no cover - overridden in app wiring/tests
    raise NotImplementedError("get_secret_key must be overridden via dependency_overrides")


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    secret_key: str = Depends(get_secret_key),
) -> str:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    from api.users.security import decode_access_token  # local import avoids a cycle at module load

    try:
        return decode_access_token(credentials.credentials, secret_key=secret_key)
    except Exception as exc:  # jwt raises various subclasses of jwt.PyJWTError
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or expired token") from exc


def _auth_error(exc: AuthError) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc))


# ── Sign-up / sign-in ──────────────────────────────────────────────────────


@router.post("/signup/password", response_model=TokenPairOut, status_code=201)
async def signup_password(
    body: SignUpWithPassword, svc: UserService = Depends(get_user_service)
) -> TokenPairOut:
    try:
        result = await svc.sign_up_with_password(
            email=body.email,
            phone=body.phone,
            password=body.password,
            display_name=body.display_name,
        )
    except AuthError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return TokenPairOut(
        access_token=result.tokens.access_token, refresh_token=result.tokens.refresh_token
    )


@router.post("/signup/guest", response_model=TokenPairOut, status_code=201)
async def signup_guest(svc: UserService = Depends(get_user_service)) -> TokenPairOut:
    result = await svc.sign_up_guest()
    return TokenPairOut(
        access_token=result.tokens.access_token, refresh_token=result.tokens.refresh_token
    )


@router.post("/signup/oauth", response_model=TokenPairOut, status_code=201)
async def signup_oauth(
    body: SignUpWithOAuth, svc: UserService = Depends(get_user_service)
) -> TokenPairOut:
    try:
        result = await svc.sign_up_or_sign_in_with_oauth(
            provider=body.provider,
            identity_token=body.identity_token,
            display_name=body.display_name,
        )
    except AuthError as exc:
        raise _auth_error(exc) from exc
    return TokenPairOut(
        access_token=result.tokens.access_token, refresh_token=result.tokens.refresh_token
    )


@router.post("/login/password", response_model=TokenPairOut)
async def login_password(
    body: LoginWithPassword, svc: UserService = Depends(get_user_service)
) -> TokenPairOut:
    try:
        result = await svc.sign_in_with_password(
            email=body.email, phone=body.phone, password=body.password
        )
    except AuthError as exc:
        raise _auth_error(exc) from exc
    return TokenPairOut(
        access_token=result.tokens.access_token, refresh_token=result.tokens.refresh_token
    )


@router.post("/token/refresh", response_model=TokenPairOut)
async def refresh_token(
    body: RefreshRequest, svc: UserService = Depends(get_user_service)
) -> TokenPairOut:
    try:
        tokens = await svc.refresh(raw_refresh_token=body.refresh_token)
    except AuthError as exc:
        raise _auth_error(exc) from exc
    return TokenPairOut(access_token=tokens.access_token, refresh_token=tokens.refresh_token)


# ── Profile & preferences ──────────────────────────────────────────────────


@router.get("/me", response_model=UserOut)
async def get_me(
    user_id: str = Depends(get_current_user_id), svc: UserService = Depends(get_user_service)
) -> Any:
    try:
        return await svc.get_user(user_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.patch("/me/preferences", response_model=UserOut)
async def update_preferences(
    body: PreferencesUpdate,
    user_id: str = Depends(get_current_user_id),
    svc: UserService = Depends(get_user_service),
) -> Any:
    return await svc.update_preferences(user_id, **body.model_dump(exclude_unset=True))


# ── Locations ──────────────────────────────────────────────────────────────


@router.post("/me/locations", response_model=LocationOut, status_code=201)
async def add_location(
    body: LocationCreate,
    user_id: str = Depends(get_current_user_id),
    svc: UserService = Depends(get_user_service),
) -> Any:
    return await svc.add_location(user_id, **body.model_dump())


@router.get("/me/locations", response_model=list[LocationOut])
async def list_locations(
    user_id: str = Depends(get_current_user_id), svc: UserService = Depends(get_user_service)
) -> Any:
    return await svc.list_locations(user_id)


@router.patch("/me/locations/{location_id}", response_model=LocationOut)
async def update_location(
    location_id: str,
    body: LocationUpdate,
    user_id: str = Depends(get_current_user_id),
    svc: UserService = Depends(get_user_service),
) -> Any:
    try:
        return await svc.update_location(
            user_id, location_id, **body.model_dump(exclude_unset=True)
        )
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.delete("/me/locations/{location_id}", status_code=204)
async def delete_location(
    location_id: str,
    user_id: str = Depends(get_current_user_id),
    svc: UserService = Depends(get_user_service),
) -> None:
    try:
        await svc.delete_location(user_id, location_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


# ── Vault ──────────────────────────────────────────────────────────────────


@router.put("/me/vault/birth-profile", status_code=204)
async def set_birth_profile(
    body: BirthProfileIn,
    user_id: str = Depends(get_current_user_id),
    svc: UserService = Depends(get_user_service),
) -> None:
    await svc.set_birth_profile(user_id, body.data)


@router.get("/me/vault/birth-profile")
async def get_birth_profile(
    user_id: str = Depends(get_current_user_id), svc: UserService = Depends(get_user_service)
) -> Any:
    return await svc.get_birth_profile(user_id)


@router.post("/me/vault/family-members", status_code=201)
async def add_family_member(
    body: FamilyMemberIn,
    user_id: str = Depends(get_current_user_id),
    svc: UserService = Depends(get_user_service),
) -> dict[str, str]:
    member_id = await svc.add_family_member(user_id, body.relation, body.data)
    return {"id": member_id}


@router.get("/me/vault/family-members")
async def list_family_members(
    user_id: str = Depends(get_current_user_id), svc: UserService = Depends(get_user_service)
) -> Any:
    return await svc.list_family_members(user_id)


# ── Account lifecycle ──────────────────────────────────────────────────────


@router.get("/me/export")
async def export_data(
    user_id: str = Depends(get_current_user_id), svc: UserService = Depends(get_user_service)
) -> Any:
    return await svc.export_data(user_id)


@router.delete("/me", status_code=204)
async def delete_account(
    user_id: str = Depends(get_current_user_id), svc: UserService = Depends(get_user_service)
) -> None:
    await svc.delete_account(user_id)
