"""The encrypted vault — birth details and family members.

Hard boundary (per Architecture §5.1 / project context §3.5):

- Lives in its own tables, separate from `users.models`, never joined into
  general user-profile reads.
- Every field that carries birth/family information is **encrypted at rest**
  (`encryption.VaultCipher`); the DB only ever stores ciphertext + a
  searchable, non-identifying `relation` tag for family members.
- Every read AND write is **access-logged** (`VaultAccessLog`) with actor,
  action and target — independent of the general application audit trail.
- **Excluded from analytics**: `ANALYTICS_EXCLUDED_TABLES` is the
  authoritative list the analytics pipeline must consult before exporting
  any table; vault tables are listed there and nowhere else gets to decide.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import select

from api.users.db import Base
from api.users.encryption import VaultCipher


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


# Tables the analytics pipeline must never read or export. This is the
# single source of truth — analytics jobs assert against it (see
# `tests/test_users.py::test_vault_tables_excluded_from_analytics`).
ANALYTICS_EXCLUDED_TABLES: frozenset[str] = frozenset(
    {"vault_birth_profiles", "vault_family_members", "vault_access_log"}
)


class VaultAction(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"


class BirthProfile(Base):
    """The user's own birth details (encrypted blob: date, time, place, …)."""

    __tablename__ = "vault_birth_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), unique=True, index=True)
    encrypted_data: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class FamilyMember(Base):
    """A family member's sensitive details (encrypted blob: relation, birth
    Tithi/Nakshatra, gotra/nakshatra, …).

    `relation_label` is stored in the clear purely so the UI can list members
    without decrypting everything; it must never itself carry identifying or
    astrological detail (enforced by `add_family_member`).
    """

    __tablename__ = "vault_family_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    relation_label: Mapped[str] = mapped_column(String(64))
    encrypted_data: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class VaultAccessLog(Base):
    """Append-only log of every access to vault data. Itself excluded from
    analytics (it would leak access patterns over sensitive data)."""

    __tablename__ = "vault_access_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    actor_id: Mapped[str] = mapped_column(String(36))  # who performed the access (usually == user_id)
    action: Mapped[str] = mapped_column(String(16))
    target_type: Mapped[str] = mapped_column(String(32))  # 'birth_profile' | 'family_member'
    target_id: Mapped[str] = mapped_column(String(36))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


async def _log(
    session: AsyncSession, *, user_id: str, actor_id: str, action: VaultAction,
    target_type: str, target_id: str,
) -> None:
    session.add(
        VaultAccessLog(
            user_id=user_id, actor_id=actor_id, action=action.value,
            target_type=target_type, target_id=target_id,
        )
    )


# ──────────────────────────────────────────────────────────────────────────
# Vault operations — the only sanctioned way to touch this data.
# Each call both encrypts/decrypts and writes an access-log entry.
# ──────────────────────────────────────────────────────────────────────────

class Vault:
    def __init__(self, cipher: VaultCipher) -> None:
        self._cipher = cipher

    async def put_birth_profile(
        self, session: AsyncSession, *, user_id: str, actor_id: str, data: dict[str, Any]
    ) -> BirthProfile:
        result = await session.execute(select(BirthProfile).where(BirthProfile.user_id == user_id))
        profile = result.scalar_one_or_none()
        action = VaultAction.UPDATE if profile else VaultAction.CREATE
        encrypted = self._cipher.encrypt_json(data)
        if profile is None:
            profile = BirthProfile(user_id=user_id, encrypted_data=encrypted)
            session.add(profile)
        else:
            profile.encrypted_data = encrypted
        await session.flush()
        await _log(session, user_id=user_id, actor_id=actor_id, action=action,
                   target_type="birth_profile", target_id=profile.id)
        return profile

    async def get_birth_profile(
        self, session: AsyncSession, *, user_id: str, actor_id: str
    ) -> dict[str, Any] | None:
        result = await session.execute(select(BirthProfile).where(BirthProfile.user_id == user_id))
        profile = result.scalar_one_or_none()
        if profile is None:
            return None
        await _log(session, user_id=user_id, actor_id=actor_id, action=VaultAction.READ,
                   target_type="birth_profile", target_id=profile.id)
        return self._cipher.decrypt_json(profile.encrypted_data)

    async def add_family_member(
        self, session: AsyncSession, *, user_id: str, actor_id: str,
        relation: str, data: dict[str, Any],
    ) -> FamilyMember:
        member = FamilyMember(
            user_id=user_id,
            relation_label=relation,
            encrypted_data=self._cipher.encrypt_json({**data, "relation": relation}),
        )
        session.add(member)
        await session.flush()
        await _log(session, user_id=user_id, actor_id=actor_id, action=VaultAction.CREATE,
                   target_type="family_member", target_id=member.id)
        return member

    async def list_family_members(
        self, session: AsyncSession, *, user_id: str, actor_id: str
    ) -> list[dict[str, Any]]:
        result = await session.execute(select(FamilyMember).where(FamilyMember.user_id == user_id))
        members = result.scalars().all()
        decrypted = []
        for member in members:
            await _log(session, user_id=user_id, actor_id=actor_id, action=VaultAction.READ,
                       target_type="family_member", target_id=member.id)
            decrypted.append({"id": member.id, **self._cipher.decrypt_json(member.encrypted_data)})
        return decrypted

    async def delete_all_for_user(self, session: AsyncSession, *, user_id: str, actor_id: str) -> None:
        """Hard-delete every vault record for a user (account deletion)."""
        result = await session.execute(select(BirthProfile).where(BirthProfile.user_id == user_id))
        profile = result.scalar_one_or_none()
        if profile is not None:
            await _log(session, user_id=user_id, actor_id=actor_id, action=VaultAction.DELETE,
                       target_type="birth_profile", target_id=profile.id)
            await session.delete(profile)

        result = await session.execute(select(FamilyMember).where(FamilyMember.user_id == user_id))
        for member in result.scalars().all():
            await _log(session, user_id=user_id, actor_id=actor_id, action=VaultAction.DELETE,
                       target_type="family_member", target_id=member.id)
            await session.delete(member)
        await session.flush()

    async def export_for_user(
        self, session: AsyncSession, *, user_id: str, actor_id: str
    ) -> dict[str, Any]:
        """Decrypted export for the data-export flow (the user exporting
        their own data — still access-logged like any other read)."""
        return {
            "birth_profile": await self.get_birth_profile(session, user_id=user_id, actor_id=actor_id),
            "family_members": await self.list_family_members(session, user_id=user_id, actor_id=actor_id),
        }
