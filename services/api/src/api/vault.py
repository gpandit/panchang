"""Provider-neutral Sensitive Vault port and deterministic local fake.

Only opaque :class:`VaultReference` values cross the ordinary application
boundary.  The fake intentionally keeps values in a private store and emits
access records containing actor, purpose, and reference metadata only.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import count
from typing import Any, Protocol
from uuid import uuid4

from sqlalchemy.orm import Session

from api.db.v3_models import VaultAccessLogRow


class VaultAccessDenied(PermissionError):
    """A reference was read outside its declared purpose/scope."""


@dataclass(frozen=True, slots=True)
class VaultReference:
    """Safe-to-serialize handle; it contains no Vault value."""

    id: str
    subject_type: str
    subject_id: str
    region: str
    purpose: str
    provider_ref: str

    def __repr__(self) -> str:
        return (
            "VaultReference("
            f"id={self.id!r}, subject_type={self.subject_type!r}, "
            f"subject_id={self.subject_id!r}, region={self.region!r}, purpose={self.purpose!r})"
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "subject_type": self.subject_type,
            "subject_id": self.subject_id,
            "region": self.region,
            "purpose": self.purpose,
            "provider_ref": self.provider_ref,
        }


@dataclass(frozen=True, slots=True)
class VaultAccessRecord:
    vault_ref_id: str
    actor_ref: str
    purpose: str
    occurred_at: datetime


class VaultAccessLogSink(Protocol):
    """Persistence seam implemented by the application's transaction layer."""

    def record(self, access: VaultAccessRecord) -> None:
        """Append one payload-free access record in the caller's transaction."""


class InMemoryVaultAccessLog:
    """Deterministic fake sink useful for contract tests."""

    def __init__(self) -> None:
        self._records: list[VaultAccessRecord] = []

    def record(self, access: VaultAccessRecord) -> None:
        self._records.append(access)

    @property
    def records(self) -> tuple[VaultAccessRecord, ...]:
        return tuple(self._records)


class SqlAlchemyVaultAccessLogSink:
    """Repository seam for the existing ``vault_access_log`` table.

    The session is deliberately not committed here: Vault access auditing and
    the surrounding domain transaction must share one commit boundary.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def record(self, access: VaultAccessRecord) -> None:
        self.session.add(
            VaultAccessLogRow(
                id=str(uuid4()),
                vault_ref_id=access.vault_ref_id,
                actor_ref=access.actor_ref,
                purpose=access.purpose,
                occurred_at=access.occurred_at,
            )
        )


class VaultPort(Protocol):
    def put(
        self,
        value: Any,
        *,
        subject_type: str,
        subject_id: str,
        region: str,
        purpose: str,
    ) -> VaultReference:
        """Store a value and return an opaque reference."""

    def read(
        self,
        reference: VaultReference,
        *,
        actor_ref: str,
        purpose: str,
        subject_id: str | None = None,
    ) -> Any:
        """Read under an exact purpose/subject scope and append an audit record."""


@dataclass(slots=True, repr=False)
class _VaultEntry:
    reference: VaultReference
    value: Any

    def __repr__(self) -> str:
        return f"_VaultEntry(reference={self.reference!r}, value=<redacted>)"


class InMemoryVault:
    """Deterministic, provider-neutral Vault fake for local and contract tests."""

    def __init__(self, *, access_log: VaultAccessLogSink | None = None) -> None:
        self._sequence = count(1)
        self._entries: dict[str, _VaultEntry] = {}
        self.access_log = access_log or InMemoryVaultAccessLog()

    def put(
        self,
        value: Any,
        *,
        subject_type: str,
        subject_id: str,
        region: str,
        purpose: str,
    ) -> VaultReference:
        number = next(self._sequence)
        opaque = f"mem-vault-{number:08d}"
        reference = VaultReference(
            id=f"vault-ref-{number:08d}",
            subject_type=subject_type,
            subject_id=subject_id,
            region=region,
            purpose=purpose,
            provider_ref=opaque,
        )
        self._entries[reference.id] = _VaultEntry(reference, deepcopy(value))
        return reference

    def read(
        self,
        reference: VaultReference,
        *,
        actor_ref: str,
        purpose: str,
        subject_id: str | None = None,
    ) -> Any:
        entry = self._entries.get(reference.id)
        if entry is None or entry.reference.provider_ref != reference.provider_ref:
            raise VaultAccessDenied("unknown Vault reference")
        if not actor_ref or purpose != entry.reference.purpose:
            raise VaultAccessDenied("Vault purpose or actor scope is not authorised")
        if subject_id is not None and subject_id != entry.reference.subject_id:
            raise VaultAccessDenied("Vault subject scope is not authorised")
        access = VaultAccessRecord(reference.id, actor_ref, purpose, datetime.now(UTC))
        self.access_log.record(access)
        return deepcopy(entry.value)

    def __repr__(self) -> str:
        return f"InMemoryVault(entries={len(self._entries)})"


__all__ = [
    "InMemoryVault",
    "InMemoryVaultAccessLog",
    "SqlAlchemyVaultAccessLogSink",
    "VaultAccessDenied",
    "VaultAccessLogSink",
    "VaultAccessRecord",
    "VaultPort",
    "VaultReference",
]
