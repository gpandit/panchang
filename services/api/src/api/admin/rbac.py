"""Admin RBAC dependency functions.

Admin tokens carry an additional `admin_role` claim.  Every admin endpoint
must declare `Depends(require_admin_role(...))`.

Token shape (extra claims passed to create_token):
    admin_role: "viewer" | "editor" | "publisher" | "super_admin"
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.auth import decode_token
from api.models.admin import AdminRole
from api.models.auth import TokenClaims

_bearer = HTTPBearer(auto_error=True)


class AdminClaims(TokenClaims):
    admin_role: AdminRole = AdminRole.VIEWER


def _get_admin_claims(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(_bearer)],
) -> AdminClaims:
    """Decode token and extract admin_role claim."""
    base = decode_token(credentials.credentials)

    import jwt
    from api.settings import get_settings

    settings = get_settings()
    payload = jwt.decode(
        credentials.credentials,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
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

    return AdminClaims(
        sub=base.sub,
        email=base.email,
        tier=base.tier,
        exp=base.exp,
        iat=base.iat,
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
