"""Sensitive Vault — store-by-reference for PII/verification artefacts (F3).

Architecture v1.2 §15.1 / north-star #7: ID images, background-check reports and
exact ceremony addresses must **never** appear in an API response or in analytics.
The tables that reference them (``pandits.payout_account_ref``,
``verification_records.vault_refs``, ``bookings.address_ref`` …) already store only
an **opaque ref string**. This module is the abstraction that mints those refs and
is the *only* sanctioned path back to the raw value.

Design contract
---------------
* ``write(...)`` encrypts the value at rest and returns a :class:`VaultRef` — an
  opaque, URL-safe token. The ref is the only thing callers persist or pass around.
* ``read(ref, *, actor, purpose)`` is the **single** way to recover the raw value.
  Every read appends a row to the access log (who, when, why). There is no
  "read without logging" entry point.
* A :class:`VaultRef` is a plain wrapper around the token. It carries **no** raw
  value, so it is safe to embed in an ORM row or Pydantic model. Serializing a
  ``VaultRef`` yields the opaque ref, never the secret — proven by the F3 tests.

Encryption
----------
There is no pre-existing vault/crypto utility in the platform to build on — the
only crypto in the codebase is ``api.auth``'s stdlib PBKDF2 password hashing, and
it deliberately pulls **no** third-party crypto dependency. This module keeps that
stance: values are sealed with a stdlib **encrypt-then-MAC** construction — a
SHA-256 counter-mode keystream for confidentiality plus an HMAC-SHA256 tag for
integrity — keyed by a vault key derived from ``settings.secret_key`` via HKDF.
No new dependency is added. (A2/verification will layer a real KMS-backed provider
behind this same ``Vault`` interface when the vendor is chosen — §A19; callers only
ever see refs, so that swap is transparent.)
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db.base import Base
from api.settings import get_settings

# ── Classification of what a vault entry holds (audit / retention hints) ───────


class VaultItemType(StrEnum):
    """What kind of sensitive artefact a vault entry holds (Architecture §12/§15.1)."""

    ID_DOCUMENT = "id_document"
    BACKGROUND_CHECK = "background_check"
    EXACT_ADDRESS = "exact_address"
    PAYOUT_ACCOUNT = "payout_account"
    OTHER = "other"


# ── ORM tables (registered on the shared Base so they build on SQLite + PG) ────


class VaultEntryRow(Base):
    """Encrypted sensitive value, addressed by its opaque ``id`` (the ref token)."""

    __tablename__ = "vault_entries"

    #: The opaque ref token handed back to callers. Random, unguessable.
    id: Mapped[str] = mapped_column(String, primary_key=True)
    item_type: Mapped[str] = mapped_column(
        String, nullable=False, default=VaultItemType.OTHER.value, index=True
    )
    #: Encrypt-then-MAC payload: nonce || ciphertext || tag. Opaque blob.
    sealed: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    #: Optional non-sensitive owner tag (e.g. pandit id) for access scoping/audit.
    owner_ref: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    access_log: Mapped[list[VaultAccessLogRow]] = relationship(
        back_populates="entry", cascade="all, delete-orphan"
    )


class VaultAccessLogRow(Base):
    """Append-only audit trail — one row per raw-value read (north-star #7)."""

    __tablename__ = "vault_access_log"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    entry_id: Mapped[str] = mapped_column(
        String, ForeignKey("vault_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    #: Who read it — a user id, admin id, or system component name.
    actor: Mapped[str] = mapped_column(String, nullable=False)
    #: Why — free-text purpose captured for the audit trail.
    purpose: Mapped[str | None] = mapped_column(String, nullable=True)
    accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    entry: Mapped[VaultEntryRow] = relationship(back_populates="access_log")


# ── The opaque reference handed to the rest of the system ──────────────────────


class VaultRef(BaseModel):
    """Opaque handle to a vaulted value. **Carries no raw secret.**

    Safe to store on an ORM row (as ``.ref``) or embed in a Pydantic response — its
    serialized form is just the opaque token. There is intentionally no field, alias
    or accessor that exposes the underlying value; recovery goes through
    :meth:`Vault.read` and is access-logged.
    """

    model_config = {"frozen": True}

    ref: str = Field(..., description="Opaque vault reference token (never the raw value)")

    def __str__(self) -> str:  # so f-strings / str() give the token, not a repr
        return self.ref


# ── Crypto helpers (stdlib only — see module docstring) ────────────────────────


def _vault_key() -> bytes:
    """Derive a 32-byte vault key from the app secret via HKDF-SHA256 (stdlib)."""
    settings = get_settings()
    ikm = settings.secret_key.encode("utf-8")
    # HKDF-Extract then a single HKDF-Expand block (32 bytes fits one SHA-256 block).
    prk = hmac.new(b"the-pandit.vault.salt", ikm, hashlib.sha256).digest()
    return hmac.new(prk, b"the-pandit.vault.key\x01", hashlib.sha256).digest()


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    """SHA-256 counter-mode keystream of ``length`` bytes."""
    out = bytearray()
    counter = 0
    while len(out) < length:
        block = hashlib.sha256(key + nonce + counter.to_bytes(8, "big")).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:length])


def _seal(plaintext: bytes) -> bytes:
    """Encrypt-then-MAC: returns nonce(16) || ciphertext || tag(32)."""
    key = _vault_key()
    nonce = secrets.token_bytes(16)
    ct = bytes(
        a ^ b for a, b in zip(plaintext, _keystream(key, nonce, len(plaintext)), strict=True)
    )
    tag = hmac.new(key, nonce + ct, hashlib.sha256).digest()
    return nonce + ct + tag


def _open(sealed: bytes) -> bytes:
    """Verify the MAC and decrypt. Raises ``ValueError`` on tamper/wrong key."""
    key = _vault_key()
    nonce, ct, tag = sealed[:16], sealed[16:-32], sealed[-32:]
    expected = hmac.new(key, nonce + ct, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected):
        raise ValueError("vault entry failed integrity check")
    return bytes(a ^ b for a, b in zip(ct, _keystream(key, nonce, len(ct)), strict=True))


def _now() -> datetime:
    return datetime.now(UTC)


# ── The vault service ──────────────────────────────────────────────────────────


class Vault:
    """Store-by-reference vault bound to an :class:`AsyncSession`.

    Usage::

        vault = Vault(session)
        ref = await vault.write("123 Temple St", item_type=VaultItemType.EXACT_ADDRESS)
        booking.address_ref = ref.ref          # persist only the opaque ref
        ...
        raw = await vault.read(ref, actor=admin_id, purpose="dispute-review")
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def write(
        self,
        value: str | bytes,
        *,
        item_type: VaultItemType = VaultItemType.OTHER,
        owner_ref: str | None = None,
    ) -> VaultRef:
        """Seal ``value`` at rest and return its opaque :class:`VaultRef`."""
        raw = value.encode("utf-8") if isinstance(value, str) else value
        ref = f"vault_{secrets.token_urlsafe(24)}"
        self._session.add(
            VaultEntryRow(
                id=ref,
                item_type=item_type.value,
                sealed=_seal(raw),
                owner_ref=owner_ref,
                created_at=_now(),
            )
        )
        await self._session.flush()
        return VaultRef(ref=ref)

    async def read(
        self,
        ref: VaultRef | str,
        *,
        actor: str,
        purpose: str | None = None,
    ) -> str:
        """Recover the raw value — the **only** de-vaulting path; always logs access.

        ``actor`` (required) and ``purpose`` are written to the append-only access
        log before the plaintext is returned. Raises ``KeyError`` if the ref is
        unknown and ``ValueError`` if the sealed blob fails its integrity check.
        """
        ref_token = ref.ref if isinstance(ref, VaultRef) else ref
        entry = await self._session.get(VaultEntryRow, ref_token)
        if entry is None:
            raise KeyError(f"unknown vault ref: {ref_token}")
        self._session.add(
            VaultAccessLogRow(
                id=f"vlog_{secrets.token_urlsafe(16)}",
                entry_id=ref_token,
                actor=actor,
                purpose=purpose,
                accessed_at=_now(),
            )
        )
        await self._session.flush()
        return _open(entry.sealed).decode("utf-8")

    async def access_log(self, ref: VaultRef | str) -> list[dict[str, Any]]:
        """Return the access history for a ref (audit / admin surfaces)."""
        ref_token = ref.ref if isinstance(ref, VaultRef) else ref
        rows = (
            await self._session.execute(
                select(VaultAccessLogRow)
                .where(VaultAccessLogRow.entry_id == ref_token)
                .order_by(VaultAccessLogRow.accessed_at)
            )
        ).scalars()
        return [
            {"actor": r.actor, "purpose": r.purpose, "accessed_at": r.accessed_at} for r in rows
        ]


__all__ = [
    "Vault",
    "VaultAccessLogRow",
    "VaultEntryRow",
    "VaultItemType",
    "VaultRef",
]
