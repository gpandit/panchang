"""Business logic for accounts, auth, preferences, locations and lifecycle.

Routers stay thin and call into `UserService`; this is what tests exercise
directly (no HTTP layer needed to assert behaviour).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.users.models import (
    AccountAuditLog,
    AuthProvider,
    Location,
    User,
)
from api.users.oauth import IdentityVerifier, InvalidIdentityToken
from api.users import security
from api.users.security import RefreshError, TokenPair
from api.users.vault import Vault


class AuthError(Exception):
    """Raised for any sign-up/sign-in failure that should surface as 401/409."""


class NotFoundError(Exception):
    pass


@dataclass(frozen=True)
class AuthResult:
    user: User
    tokens: TokenPair


def _now() -> datetime:
    return datetime.now(timezone.utc)


class UserService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        secret_key: str,
        vault: Vault,
        oauth_verifiers: dict[AuthProvider, IdentityVerifier] | None = None,
    ) -> None:
        self._session = session
        self._secret_key = secret_key
        self._vault = vault
        self._oauth_verifiers = oauth_verifiers or {}

    # ── Sign-up / sign-in ─────────────────────────────────────────────────

    async def sign_up_with_password(
        self, *, email: str | None, phone: str | None, password: str, display_name: str | None
    ) -> AuthResult:
        if not email and not phone:
            raise AuthError("email or phone is required")
        existing = await self._find_by_identity(email=email, phone=phone)
        if existing is not None:
            raise AuthError("an account with this email/phone already exists")

        user = User(
            email=email,
            phone=phone,
            password_hash=security.hash_password(password),
            auth_provider=AuthProvider.PASSWORD.value,
            display_name=display_name,
        )
        self._session.add(user)
        await self._session.flush()
        tokens = await security.issue_token_pair(self._session, user_id=user.id, secret_key=self._secret_key)
        return AuthResult(user=user, tokens=tokens)

    async def sign_up_guest(self) -> AuthResult:
        user = User(is_guest=True, auth_provider=AuthProvider.GUEST.value)
        self._session.add(user)
        await self._session.flush()
        tokens = await security.issue_token_pair(self._session, user_id=user.id, secret_key=self._secret_key)
        return AuthResult(user=user, tokens=tokens)

    async def sign_up_or_sign_in_with_oauth(
        self, *, provider: AuthProvider, identity_token: str, display_name: str | None
    ) -> AuthResult:
        verifier = self._oauth_verifiers.get(provider)
        if verifier is None:
            raise AuthError(f"{provider.value} sign-in is not configured")
        try:
            identity = verifier.verify(identity_token)
        except InvalidIdentityToken as exc:
            raise AuthError(str(exc)) from exc

        result = await self._session.execute(
            select(User).where(
                User.auth_provider == provider.value,
                User.provider_subject == identity.subject,
            )
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                email=identity.email,
                auth_provider=provider.value,
                provider_subject=identity.subject,
                display_name=display_name,
            )
            self._session.add(user)
            await self._session.flush()

        tokens = await security.issue_token_pair(self._session, user_id=user.id, secret_key=self._secret_key)
        return AuthResult(user=user, tokens=tokens)

    async def sign_in_with_password(
        self, *, email: str | None, phone: str | None, password: str
    ) -> AuthResult:
        user = await self._find_by_identity(email=email, phone=phone)
        if user is None or user.password_hash is None:
            raise AuthError("invalid credentials")
        if not security.verify_password(password, user.password_hash):
            raise AuthError("invalid credentials")
        if user.is_deleted:
            raise AuthError("account has been deleted")

        tokens = await security.issue_token_pair(self._session, user_id=user.id, secret_key=self._secret_key)
        return AuthResult(user=user, tokens=tokens)

    async def refresh(self, *, raw_refresh_token: str) -> TokenPair:
        try:
            return await security.rotate_refresh_token(
                self._session, raw_refresh_token=raw_refresh_token, secret_key=self._secret_key
            )
        except RefreshError as exc:
            raise AuthError(str(exc)) from exc

    async def _find_by_identity(self, *, email: str | None, phone: str | None) -> User | None:
        if email:
            result = await self._session.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if user is not None:
                return user
        if phone:
            result = await self._session.execute(select(User).where(User.phone == phone))
            return result.scalar_one_or_none()
        return None

    # ── Profile & preferences ─────────────────────────────────────────────

    async def get_user(self, user_id: str) -> User:
        user = await self._session.get(User, user_id)
        if user is None or user.is_deleted:
            raise NotFoundError("user not found")
        return user

    async def update_preferences(self, user_id: str, **fields: Any) -> User:
        user = await self.get_user(user_id)
        for key, value in fields.items():
            if value is None:
                continue
            value = value.value if hasattr(value, "value") else value
            setattr(user, key, value)
        await self._session.flush()
        return user

    # ── Locations ─────────────────────────────────────────────────────────

    async def add_location(self, user_id: str, **fields: Any) -> Location:
        await self.get_user(user_id)
        location = Location(user_id=user_id, **fields)
        self._session.add(location)
        await self._session.flush()
        return location

    async def list_locations(self, user_id: str) -> list[Location]:
        result = await self._session.execute(select(Location).where(Location.user_id == user_id))
        return list(result.scalars().all())

    async def update_location(self, user_id: str, location_id: str, **fields: Any) -> Location:
        location = await self._get_owned_location(user_id, location_id)
        for key, value in fields.items():
            if value is not None:
                setattr(location, key, value)
        await self._session.flush()
        return location

    async def delete_location(self, user_id: str, location_id: str) -> None:
        location = await self._get_owned_location(user_id, location_id)
        await self._session.delete(location)
        await self._session.flush()

    async def _get_owned_location(self, user_id: str, location_id: str) -> Location:
        location = await self._session.get(Location, location_id)
        if location is None or location.user_id != user_id:
            raise NotFoundError("location not found")
        return location

    # ── Vault (delegated; this is the only path the API exposes to it) ────

    async def set_birth_profile(self, user_id: str, data: dict[str, Any]) -> None:
        await self.get_user(user_id)
        await self._vault.put_birth_profile(self._session, user_id=user_id, actor_id=user_id, data=data)

    async def get_birth_profile(self, user_id: str) -> dict[str, Any] | None:
        await self.get_user(user_id)
        return await self._vault.get_birth_profile(self._session, user_id=user_id, actor_id=user_id)

    async def add_family_member(self, user_id: str, relation: str, data: dict[str, Any]) -> str:
        await self.get_user(user_id)
        member = await self._vault.add_family_member(
            self._session, user_id=user_id, actor_id=user_id, relation=relation, data=data
        )
        return member.id

    async def list_family_members(self, user_id: str) -> list[dict[str, Any]]:
        await self.get_user(user_id)
        return await self._vault.list_family_members(self._session, user_id=user_id, actor_id=user_id)

    # ── Account lifecycle ─────────────────────────────────────────────────

    async def export_data(self, user_id: str) -> dict[str, Any]:
        """Produce a complete archive of everything we hold on the user,
        including decrypted vault contents (their own data, on their request)."""
        user = await self.get_user(user_id)
        locations = await self.list_locations(user_id)
        vault_data = await self._vault.export_for_user(self._session, user_id=user_id, actor_id=user_id)

        archive = {
            "profile": {
                "id": user.id,
                "email": user.email,
                "phone": user.phone,
                "display_name": user.display_name,
                "is_guest": user.is_guest,
                "preferred_calendar_system": user.preferred_calendar_system,
                "language": user.language,
                "time_form": user.time_form,
                "ayanamsa_override": user.ayanamsa_override,
                "notification_settings": user.notification_settings,
                "created_at": user.created_at.isoformat(),
            },
            "locations": [
                {
                    "id": loc.id, "label": loc.label, "lat": loc.lat, "lon": loc.lon,
                    "tz": loc.tz, "dst_rule": loc.dst_rule,
                    "is_favourite": loc.is_favourite, "is_travel_mode": loc.is_travel_mode,
                }
                for loc in locations
            ],
            "vault": vault_data,
        }

        self._session.add(AccountAuditLog(user_id=user_id, action="data_exported"))
        await self._session.flush()
        return archive

    async def delete_account(self, user_id: str) -> None:
        """Hard-delete the account: vault data, locations, refresh tokens,
        and the user row itself, with the action audited.

        The audit row is written under the user's id *before* the user row
        is removed for FK integrity reasons in some backends, but the audit
        log is keyed by id (not a live FK) so it survives the deletion.
        """
        user = await self.get_user(user_id)

        await self._vault.delete_all_for_user(self._session, user_id=user_id, actor_id=user_id)

        self._session.add(AccountAuditLog(user_id=user_id, action="account_deleted"))
        await self._session.flush()

        await self._session.delete(user)
        await self._session.flush()
