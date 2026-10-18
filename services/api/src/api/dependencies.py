"""FastAPI dependency functions.

Usage in routers:
    from api.dependencies import require_auth, require_tier

    @router.get("/...")
    async def my_endpoint(claims: Annotated[TokenClaims, Depends(require_auth)]):
        ...

    # Gated endpoint — returns 403 if caller is below silver
    @router.get("/gated")
    async def gated(claims: Annotated[TokenClaims, Depends(require_tier(SubscriptionTier.SILVER))]):
        ...
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import decode_token
from api.db import get_session
from api.db.v3_models import UserRow
from api.identity import IdentityError, IdentityService
from api.models.auth import AccountRole, SubscriptionTier, TokenClaims

_bearer = HTTPBearer(auto_error=True)


def require_auth(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(_bearer)],
) -> TokenClaims:
    """Validate Bearer JWT and return typed claims.  Raises 401 on failure."""
    return decode_token(credentials.credentials)


def require_tier(
    min_tier: SubscriptionTier,
) -> Callable[[Annotated[TokenClaims, object]], TokenClaims]:
    """Return a FastAPI dependency that enforces a minimum subscription tier.

    Usage:  Depends(require_tier(SubscriptionTier.SILVER))
    """

    def _check(claims: Annotated[TokenClaims, Depends(require_auth)]) -> TokenClaims:
        if not claims.tier.meets(min_tier):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "insufficient_tier",
                    "message": f"This endpoint requires {min_tier.value} or above. "
                    f"Your tier: {claims.tier.value}.",
                },
            )
        return claims

    return _check


async def require_user(
    claims: Annotated[TokenClaims, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserRow:
    """Resolve the authenticated subject to an active, persisted user."""
    try:
        return await IdentityService(session).resolve(claims)
    except IdentityError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


async def require_user_for_deletion(
    claims: Annotated[TokenClaims, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserRow:
    """Resolve an account while allowing an existing deletion request to replay."""
    try:
        return await IdentityService(session).resolve(claims, allow_deleting=True)
    except IdentityError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


def require_role(
    role: AccountRole,
) -> Callable[..., Awaitable[UserRow]]:
    """Return a dependency enforcing a role from the persisted account record."""

    async def _check(user: Annotated[UserRow, Depends(require_user)]) -> UserRow:
        if role.value not in (user.roles or []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "insufficient_role", "message": "This role is required."},
            )
        return user

    return _check
