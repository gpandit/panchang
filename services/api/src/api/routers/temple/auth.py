"""Temple-admin authentication — email + password login.

``POST /temple/v1/auth/login`` verifies credentials against the temple store and
mints a JWT carrying the account's ``temple_id``. ``GET /temple/v1/auth/me`` returns
the assigned temple for the logged-in admin.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.auth import create_temple_token, verify_password
from api.models.temple import LoginIn, LoginOut, TempleConfig
from api.temple import store
from api.temple.rbac import TempleClaims, require_temple_admin

router = APIRouter(prefix="/auth", tags=["temple-auth"])

_TempleDep = Annotated[TempleClaims, Depends(require_temple_admin)]


@router.post("/login", response_model=LoginOut)
async def login(payload: LoginIn) -> LoginOut:
    account = store.get_account_by_email(payload.email)
    if account is None or not verify_password(
        payload.password, password_hash=account.password_hash, salt=account.salt
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_credentials", "message": "Invalid email or password."},
        )
    token = create_temple_token(account.id, account.temple_id, email=account.email)
    return LoginOut(token=token, temple_id=account.temple_id)


@router.get("/me", response_model=TempleConfig)
async def me(claims: _TempleDep) -> TempleConfig:
    temple = store.get_temple(claims.temple_id)
    if temple is None:
        raise HTTPException(status_code=404, detail="Assigned temple not found")
    return temple
