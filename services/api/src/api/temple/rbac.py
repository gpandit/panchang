"""Temple-admin RBAC dependency.

Temple-admin tokens carry a ``temple_id`` claim binding the caller to one temple.
Every authenticated temple endpoint declares ``Depends(require_temple_admin)``.

Mirrors ``api.admin.rbac`` but gates on the presence of a ``temple_id`` claim
rather than an ``admin_role``.
"""

from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.models.auth import SubscriptionTier, TokenClaims
from api.settings import get_settings

_bearer = HTTPBearer(auto_error=True)


class TempleClaims(TokenClaims):
    temple_id: str


def require_temple_admin(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(_bearer)],
) -> TempleClaims:
    """Decode the JWT and require a ``temple_id`` claim. 401 on bad token, 403 if not a temple admin."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except (jwt.DecodeError, jwt.InvalidTokenError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    temple_id = payload.get("temple_id")
    if not temple_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "not_temple_admin",
                "message": "This endpoint requires a temple-admin token.",
            },
        )

    tier_raw = payload.get("tier", "basic")
    try:
        tier = SubscriptionTier(tier_raw)
    except ValueError:
        tier = SubscriptionTier.BASIC

    return TempleClaims(
        sub=payload["sub"],
        email=payload.get("email"),
        tier=tier,
        exp=payload.get("exp"),
        iat=payload.get("iat"),
        temple_id=temple_id,
    )
