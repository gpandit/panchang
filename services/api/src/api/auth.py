"""JWT decode/validate helpers.

In production the gateway validates JWTs issued by the auth service (Step 2.1).
For dev/test, tokens are signed with the symmetric `secret_key` using HS256.

Callers should use `decode_token` — it raises HTTPException on any failure
so FastAPI dependency injection propagates 401 directly.
"""

from __future__ import annotations

import jwt
from fastapi import HTTPException, status
from jwt.exceptions import DecodeError, ExpiredSignatureError, InvalidTokenError

from api.models.auth import SubscriptionTier, TokenClaims
from api.settings import get_settings


def decode_token(token: str) -> TokenClaims:
    """Decode and validate a JWT, returning typed claims.

    Raises HTTPException 401 on any validation failure.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except (DecodeError, InvalidTokenError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    tier_raw = payload.get("tier", "basic")
    try:
        tier = SubscriptionTier(tier_raw)
    except ValueError:
        tier = SubscriptionTier.BASIC

    return TokenClaims(
        sub=payload["sub"],
        email=payload.get("email"),
        tier=tier,
        exp=payload.get("exp"),
        iat=payload.get("iat"),
    )


def create_admin_token(sub: str, admin_role: str, **extra: object) -> str:
    """Create a JWT with an admin_role claim — used in tests and the admin auth stub."""
    return create_token(sub, tier=SubscriptionTier.BASIC, admin_role=admin_role, **extra)


def create_token(sub: str, tier: SubscriptionTier = SubscriptionTier.BASIC, **extra: object) -> str:
    """Create a signed JWT — used in tests and by the auth service stub."""
    import time

    settings = get_settings()
    payload: dict[str, object] = {
        "sub": sub,
        "tier": tier.value,
        "iat": int(time.time()),
        "exp": int(time.time()) + settings.access_token_expire_seconds,
        **extra,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
