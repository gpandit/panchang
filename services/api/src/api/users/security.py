"""Password hashing, access/refresh token issuance, and refresh rotation.

Refresh tokens are opaque random strings; only their hash is persisted
(`RefreshToken.token_hash`). Each use rotates the token: the old one is
marked `revoked_at`/`replaced_by_id` and a new one issued. Presenting an
already-rotated token revokes the *entire* chain — a signal of token theft.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.users.models import RefreshToken

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=30)


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd_context.verify(password, password_hash)


def issue_access_token(*, user_id: str, secret_key: str, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    payload = {"sub": user_id, "type": "access", "iat": now, "exp": now + ACCESS_TOKEN_TTL}
    return jwt.encode(payload, secret_key, algorithm="HS256")


def decode_access_token(token: str, *, secret_key: str) -> str:
    """Return the user id encoded in a valid access token, or raise."""
    payload = jwt.decode(token, secret_key, algorithms=["HS256"])
    if payload.get("type") != "access":
        raise ValueError("not an access token")
    return payload["sub"]


def _aware(dt: datetime) -> datetime:
    """SQLite drops tzinfo on round-trip; coerce back to UTC-aware for comparison."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str


async def issue_token_pair(
    session: AsyncSession, *, user_id: str, secret_key: str, now: datetime | None = None
) -> TokenPair:
    now = now or datetime.now(timezone.utc)
    raw_refresh = secrets.token_urlsafe(48)
    session.add(
        RefreshToken(
            user_id=user_id,
            token_hash=_hash_refresh_token(raw_refresh),
            expires_at=now + REFRESH_TOKEN_TTL,
        )
    )
    await session.flush()
    return TokenPair(
        access_token=issue_access_token(user_id=user_id, secret_key=secret_key, now=now),
        refresh_token=raw_refresh,
    )


class RefreshError(Exception):
    """Raised when a refresh token is invalid, expired, revoked, or reused."""


async def rotate_refresh_token(
    session: AsyncSession, *, raw_refresh_token: str, secret_key: str, now: datetime | None = None
) -> TokenPair:
    """Validate *raw_refresh_token*, revoke it, and issue a fresh pair.

    If the presented token was already rotated (`replaced_by_id` set), the
    whole chain is revoked — treat this as theft detection.
    """
    now = now or datetime.now(timezone.utc)
    token_hash = _hash_refresh_token(raw_refresh_token)
    result = await session.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    token = result.scalar_one_or_none()
    if token is None:
        raise RefreshError("unknown refresh token")

    if token.revoked_at is not None:
        await _revoke_chain_from(session, token, now=now)
        raise RefreshError("refresh token reuse detected — chain revoked")

    if _aware(token.expires_at) <= now:
        raise RefreshError("refresh token expired")

    raw_new = secrets.token_urlsafe(48)
    new_token = RefreshToken(
        user_id=token.user_id,
        token_hash=_hash_refresh_token(raw_new),
        expires_at=now + REFRESH_TOKEN_TTL,
    )
    session.add(new_token)
    await session.flush()

    token.revoked_at = now
    token.replaced_by_id = new_token.id

    return TokenPair(
        access_token=issue_access_token(user_id=token.user_id, secret_key=secret_key, now=now),
        refresh_token=raw_new,
    )


async def _revoke_chain_from(session: AsyncSession, token: RefreshToken, *, now: datetime) -> None:
    current: RefreshToken | None = token
    seen: set[str] = set()
    while current is not None and current.id not in seen:
        seen.add(current.id)
        if current.revoked_at is None:
            current.revoked_at = now
        next_id = current.replaced_by_id
        if next_id is None:
            break
        result = await session.execute(select(RefreshToken).where(RefreshToken.id == next_id))
        current = result.scalar_one_or_none()
