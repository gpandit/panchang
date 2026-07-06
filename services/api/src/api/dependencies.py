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

    # Role-gated endpoint (F3) — returns 403 if caller lacks the pandit role
    @router.get("/provider")
    async def provider(claims: Annotated[TokenClaims, Depends(require_role(Role.PANDIT))]):
        ...
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.auth import decode_token
from api.models.auth import Role, SubscriptionTier, TokenClaims

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


def require_role(
    *required: Role,
) -> Callable[[Annotated[TokenClaims, object]], TokenClaims]:
    """Return a FastAPI dependency that enforces marketplace role membership (F3).

    Mirrors :func:`require_tier` (same style, same 403 detail shape) but for the
    unordered ``roles`` set rather than a graduated tier. Pass one role to gate a
    single capability, or several to require the caller hold **all** of them::

        Depends(require_role(Role.PANDIT))            # provider-only endpoint
        Depends(require_role(Role.PATRON, Role.PANDIT))  # dual-role required

    A caller may of course hold *more* roles than required; only the required set
    must be a subset of the caller's roles.
    """

    required_set = set(required)

    def _check(claims: Annotated[TokenClaims, Depends(require_auth)]) -> TokenClaims:
        if not required_set <= claims.roles:
            missing = required_set - claims.roles
            want = ", ".join(sorted(r.value for r in missing))
            have = ", ".join(sorted(r.value for r in claims.roles)) or "none"
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "insufficient_role",
                    "message": f"This endpoint requires role(s): {want}. Your roles: {have}.",
                },
            )
        return claims

    return _check
