"""JWT decode/validate helpers.

In production the gateway validates JWTs issued by the auth service (Step 2.1).
For dev/test, tokens are signed with the symmetric `secret_key` using HS256.

Callers should use `decode_token` — it raises HTTPException on any failure
so FastAPI dependency injection propagates 401 directly.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

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


def create_temple_token(sub: str, temple_id: str, email: str | None = None) -> str:
    """Create a JWT carrying a `temple_id` claim — identifies a temple admin."""
    return create_token(sub, tier=SubscriptionTier.BASIC, temple_id=temple_id, email=email)


# ── Password hashing (PBKDF2-HMAC-SHA256, stdlib — no extra deps) ─────────────

_PBKDF2_ITERATIONS = 200_000


def hash_password(password: str, *, salt: str | None = None) -> tuple[str, str]:
    """Hash a password with PBKDF2. Returns (hex_hash, hex_salt).

    Pass an existing salt to reproduce a stored hash for verification.
    """
    salt_hex = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), _PBKDF2_ITERATIONS
    )
    return digest.hex(), salt_hex


def verify_password(password: str, *, password_hash: str, salt: str) -> bool:
    """Constant-time check of a password against a stored (hash, salt)."""
    candidate, _ = hash_password(password, salt=salt)
    return hmac.compare_digest(candidate, password_hash)


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
