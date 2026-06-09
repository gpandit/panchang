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

from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.auth import decode_token
from api.models.auth import SubscriptionTier, TokenClaims

_bearer = HTTPBearer(auto_error=True)


def require_auth(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(_bearer)],
) -> TokenClaims:
    """Validate Bearer JWT and return typed claims.  Raises 401 on failure."""
    return decode_token(credentials.credentials)


def require_tier(min_tier: SubscriptionTier):
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
