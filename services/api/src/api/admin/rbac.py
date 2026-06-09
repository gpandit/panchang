"""Admin RBAC dependency functions.

Admin tokens carry an additional `admin_role` claim.  Every admin endpoint
must declare `Depends(require_admin_role(...))`.

Token shape (extra claims passed to create_token):
    admin_role: "viewer" | "editor" | "publisher" | "super_admin"
"""

from __future__ import annotations

import jwt
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.models.admin import AdminRole
from api.models.auth import SubscriptionTier, TokenClaims
from api.settings import get_settings

_bearer = HTTPBearer(auto_error=True)


class AdminClaims(TokenClaims):
    admin_role: AdminRole = AdminRole.VIEWER


def _get_admin_claims(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(_bearer)],
) -> AdminClaims:
    """Decode the JWT once and extract both standard claims and admin_role."""
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
        )
    except (jwt.DecodeError, jwt.InvalidTokenError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role_raw = payload.get("admin_role", "")
    try:
        role = AdminRole(role_raw)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "not_admin",
                "message": "This endpoint requires an admin role.",
            },
        )

    tier_raw = payload.get("tier", "basic")
    try:
        tier = SubscriptionTier(tier_raw)
    except ValueError:
        tier = SubscriptionTier.BASIC

    return AdminClaims(
        sub=payload["sub"],
        email=payload.get("email"),
        tier=tier,
        exp=payload.get("exp"),
        iat=payload.get("iat"),
        admin_role=role,
    )


def require_admin_role(min_role: AdminRole):
    """Return a FastAPI dependency that enforces a minimum admin role."""

    def _check(claims: Annotated[AdminClaims, Depends(_get_admin_claims)]) -> AdminClaims:
        if not claims.admin_role.meets(min_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "insufficient_admin_role",
                    "message": (
                        f"This endpoint requires admin role '{min_role.value}' or above. "
                        f"Your role: '{claims.admin_role.value}'."
                    ),
                },
            )
        return claims

    return _check
