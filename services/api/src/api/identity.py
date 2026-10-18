"""Persistent identity/profile boundary for S2-01.

The service keeps authentication claims as an external identity hint only.  The
database row is authoritative for tier, roles, lifecycle state, preferences, and
ownership.  Sensitive birth data is written to the Vault port and only its
opaque reference is persisted in the application database.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.v3_models import (
    LocationRow,
    UserJobRow,
    UserPreferenceRow,
    UserRow,
    VaultRefRow,
)
from api.models.auth import AccountRole, SubscriptionTier, TokenClaims
from api.models.user import BirthDetailsIn, LocationIn, LocationOut, ProfileOut, ProfileUpdateIn
from api.outbox import OutboxRepository
from api.settings import get_settings
from api.vault import InMemoryVault, VaultPort, VaultReference


class IdentityError(Exception):
    """A safe, user-facing identity-domain failure."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


_vault = InMemoryVault()


def get_vault() -> VaultPort:
    """Return the configured provider seam; production wiring replaces this fake."""
    return _vault


def _tier(value: str) -> SubscriptionTier:
    try:
        return SubscriptionTier(value)
    except ValueError:
        return SubscriptionTier.BASIC


def _location_out(row: LocationRow) -> LocationOut:
    return LocationOut(
        id=row.id,
        name=row.label,
        lat=float(row.lat),
        lon=float(row.lon),
        tz=row.timezone,
        is_default=bool(row.is_primary),
    )


class IdentityService:
    """Coordinate user persistence, location ownership, Vault refs, and outbox writes."""

    def __init__(self, session: AsyncSession, *, vault: VaultPort | None = None) -> None:
        self.session = session
        self.vault = vault or get_vault()

    async def resolve(self, claims: TokenClaims, *, allow_deleting: bool = False) -> UserRow:
        result = await self.session.execute(
            select(UserRow).where(UserRow.auth_subject_ref == claims.sub)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = UserRow(
                id=str(uuid4()),
                auth_subject_ref=claims.sub,
                email_ref=claims.email,
                tier=claims.tier.value,
                roles=[AccountRole.PATRON.value],
                status="active",
            )
            self.session.add(user)
            self.session.add(UserPreferenceRow(user_id=user.id))
            await self.session.flush()
        elif user.status != "active" and not (allow_deleting and user.status == "deleting"):
            code = "account_deleted" if user.status == "deleted" else "account_deletion_pending"
            status_code = 410 if user.status == "deleted" else 403
            raise IdentityError(code, "This account is not available.", status_code)
        return user

    async def profile(self, user: UserRow) -> ProfileOut:
        pref = await self._preferences(user)
        locations = await self.list_locations(user)
        birth = await self._birth_ref(user.id)
        return ProfileOut(
            user_id=user.id,
            email=user.email_ref,
            display_name=user.display_name,
            default_ayanamsa=pref.ayanamsa,
            default_month_scheme=pref.scheme,
            locations=locations,
            tier=_tier(user.tier).value,
            roles=list(user.roles or []),
            has_birth_details=birth is not None,
        )

    async def update_profile(self, user: UserRow, body: ProfileUpdateIn) -> ProfileOut:
        if body.default_ayanamsa is not None:
            if body.default_ayanamsa not in {"lahiri", "raman", "krishnamurti"}:
                raise IdentityError("invalid_ayanamsa", "Unsupported ayanamsa.")
        if body.default_month_scheme is not None:
            if body.default_month_scheme not in {"amanta", "purnimanta"}:
                raise IdentityError("invalid_month_scheme", "Unsupported month scheme.")
        if "display_name" in body.model_fields_set:
            user.display_name = body.display_name
        pref = await self._preferences(user)
        if body.default_ayanamsa is not None:
            pref.ayanamsa = body.default_ayanamsa
        if body.default_month_scheme is not None:
            pref.scheme = body.default_month_scheme
        await self.session.flush()
        return await self.profile(user)

    async def list_locations(self, user: UserRow) -> list[LocationOut]:
        result = await self.session.execute(
            select(LocationRow)
            .where(LocationRow.user_id == user.id)
            .order_by(LocationRow.created_at, LocationRow.id)
        )
        return [_location_out(row) for row in result.scalars().all()]

    async def add_location(self, user: UserRow, body: LocationIn) -> LocationOut:
        result = await self.session.execute(
            select(LocationRow).where(LocationRow.user_id == user.id)
        )
        existing = list(result.scalars().all())
        tier = _tier(user.tier)
        limits = {
            SubscriptionTier.BASIC: 1,
            SubscriptionTier.SILVER: 3,
            SubscriptionTier.GOLD: None,
        }
        limit = limits[tier]
        if limit is not None and len(existing) >= limit:
            raise IdentityError(
                "location_limit_reached",
                f"{tier.value} accounts can save up to {limit} location(s).",
                403,
            )

        is_primary = body.is_default or not existing
        if is_primary and existing:
            await self.session.execute(
                update(LocationRow).where(LocationRow.user_id == user.id).values(is_primary=False)
            )
        row = LocationRow(
            id=str(uuid4()),
            user_id=user.id,
            label=body.name,
            lat=body.lat,
            lon=body.lon,
            timezone=body.tz,
            is_primary=is_primary,
        )
        self.session.add(row)
        await self.session.flush()
        await OutboxRepository(self.session).enqueue(
            aggregate_type="user",
            aggregate_id=user.id,
            event_type="user.location_changed",
            payload_ref=f"user-location://{row.id}",
            dedupe_key=f"user:{user.id}:location:{row.id}:created",
        )
        return _location_out(row)

    async def delete_location(self, user: UserRow, location_id: str) -> None:
        result = await self.session.execute(
            select(LocationRow).where(LocationRow.id == location_id, LocationRow.user_id == user.id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise IdentityError("location_not_found", "Location not found.", 404)
        was_primary = bool(row.is_primary)
        await self.session.delete(row)
        await self.session.flush()
        if was_primary:
            replacement = await self.session.execute(
                select(LocationRow)
                .where(LocationRow.user_id == user.id)
                .order_by(LocationRow.created_at, LocationRow.id)
                .limit(1)
            )
            next_row = replacement.scalar_one_or_none()
            if next_row is not None:
                next_row.is_primary = True
        await OutboxRepository(self.session).enqueue(
            aggregate_type="user",
            aggregate_id=user.id,
            event_type="user.location_changed",
            payload_ref=f"user-location://{location_id}",
            dedupe_key=f"user:{user.id}:location:{location_id}:deleted",
        )

    async def set_birth_details(self, user: UserRow, body: BirthDetailsIn) -> None:
        old = await self._birth_ref(user.id)
        if old is not None:
            self.vault.delete(_reference(old), actor_ref=user.auth_subject_ref, purpose=old.purpose)
            await self.session.delete(old)
            await self.session.flush()
        reference = self.vault.put(
            body.model_dump(mode="json"),
            subject_type="user",
            subject_id=user.id,
            region=get_settings().vault_region,
            purpose="birth_details",
        )
        self.session.add(
            VaultRefRow(
                id=reference.id,
                subject_type=reference.subject_type,
                subject_id=reference.subject_id,
                region=reference.region,
                purpose=reference.purpose,
                provider_ref=reference.provider_ref,
            )
        )
        await self.session.flush()

    async def delete_birth_details(self, user: UserRow) -> None:
        row = await self._birth_ref(user.id)
        if row is None:
            return
        self.vault.delete(_reference(row), actor_ref=user.auth_subject_ref, purpose=row.purpose)
        await self.session.delete(row)
        await self.session.flush()

    async def request_export(self, user: UserRow) -> UserJobRow:
        return await self._request_job(user, "export", "user.export_requested")

    async def request_deletion(self, user: UserRow) -> UserJobRow:
        existing = await self._open_job(user, "deletion")
        if existing is not None:
            return existing
        user.status = "deleting"
        user.deletion_requested_at = datetime.now(UTC)
        job = UserJobRow(id=str(uuid4()), user_id=user.id, kind="deletion", status="queued")
        self.session.add(job)
        await self.session.flush()
        await OutboxRepository(self.session).enqueue(
            aggregate_type="user",
            aggregate_id=user.id,
            event_type="user.deletion_requested",
            payload_ref=f"user-deletion://{job.id}",
            dedupe_key=f"user:{user.id}:deletion",
        )
        return job

    async def erase_sensitive_data(self, user: UserRow) -> None:
        """Worker-facing erasure step; preserve a tombstone for audit/revocation."""
        refs = await self.session.execute(
            select(VaultRefRow).where(
                VaultRefRow.subject_type == "user", VaultRefRow.subject_id == user.id
            )
        )
        for ref in refs.scalars().all():
            self.vault.delete(_reference(ref), actor_ref=user.auth_subject_ref, purpose=ref.purpose)
            await self.session.delete(ref)
        user.display_name = None
        user.email_ref = None
        user.phone_ref = None
        user.roles = []
        user.status = "deleted"
        user.deleted_at = datetime.now(UTC)
        await self.session.flush()

    async def _preferences(self, user: UserRow) -> UserPreferenceRow:
        pref = await self.session.get(UserPreferenceRow, user.id)
        if pref is None:
            pref = UserPreferenceRow(user_id=user.id)
            self.session.add(pref)
            await self.session.flush()
        return pref

    async def _birth_ref(self, user_id: str) -> VaultRefRow | None:
        result = await self.session.execute(
            select(VaultRefRow).where(
                VaultRefRow.subject_type == "user",
                VaultRefRow.subject_id == user_id,
                VaultRefRow.purpose == "birth_details",
            )
        )
        return result.scalar_one_or_none()

    async def _open_job(self, user: UserRow, kind: str) -> UserJobRow | None:
        result = await self.session.execute(
            select(UserJobRow)
            .where(
                UserJobRow.user_id == user.id,
                UserJobRow.kind == kind,
                UserJobRow.status.in_(("queued", "processing")),
            )
            .order_by(UserJobRow.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _request_job(self, user: UserRow, kind: str, event_type: str) -> UserJobRow:
        existing = await self._open_job(user, kind)
        if existing is not None:
            return existing
        job = UserJobRow(id=str(uuid4()), user_id=user.id, kind=kind, status="queued")
        self.session.add(job)
        await self.session.flush()
        await OutboxRepository(self.session).enqueue(
            aggregate_type="user",
            aggregate_id=user.id,
            event_type=event_type,
            payload_ref=f"user-{kind}://{job.id}",
            dedupe_key=f"user:{user.id}:{kind}:{job.id}",
        )
        return job


def _reference(row: VaultRefRow) -> VaultReference:
    return VaultReference(
        id=row.id,
        subject_type=row.subject_type,
        subject_id=row.subject_id,
        region=row.region,
        purpose=row.purpose,
        provider_ref=row.provider_ref,
    )


__all__ = ["IdentityError", "IdentityService", "get_vault"]
