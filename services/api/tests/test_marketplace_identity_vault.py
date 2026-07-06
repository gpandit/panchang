"""Tests for F3 — dual-role identity + Vault references.

Two concerns, mirroring the F3 acceptance criteria:

1. **Dual-role identity / ``require_role``** — a JWT carrying the ``pandit`` role
   passes ``require_role(Role.PANDIT)``; a patron-only JWT is rejected with the
   **same 403 shape** ``require_tier`` uses (``detail.code`` / ``detail.message``).
   Proven end-to-end through a tiny FastAPI app that mounts the real dependency,
   plus direct unit assertions on claim parsing.

2. **Vault references** — a write returns an opaque ref; reads are access-logged;
   and the raw value is provably **absent from any API response model** (a
   ``VaultRef`` serializes to just the token, and an ORM/response object that
   carries a ref never exposes the plaintext).

All DB-touching tests run on the shared in-memory SQLite engine (no Postgres),
following the F2 ``tests/test_marketplace_schema.py`` pattern.
"""

from __future__ import annotations

from typing import Annotated

import pytest
from fastapi import Depends, FastAPI, status
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.auth import create_token, decode_token
from api.db import Base
from api.dependencies import require_role
from api.marketplace.vault import Vault, VaultEntryRow, VaultItemType, VaultRef
from api.models.auth import Role, SubscriptionTier, TokenClaims

# ── Dual-role identity: claims plumbing ────────────────────────────────────────


def test_token_carries_roles_roundtrip() -> None:
    token = create_token("u1", roles=[Role.PATRON, Role.PANDIT])
    claims = decode_token(token)
    assert claims.roles == {Role.PATRON, Role.PANDIT}
    assert claims.has_role(Role.PANDIT)
    assert claims.has_role(Role.PATRON)


def test_legacy_token_has_empty_roles() -> None:
    """A pre-marketplace token (no ``roles`` claim) decodes to an empty role set."""
    claims = decode_token(create_token("u1", tier=SubscriptionTier.GOLD))
    assert claims.roles == set()
    assert not claims.has_role(Role.PANDIT)


def test_unknown_role_string_is_dropped_not_fatal() -> None:
    """A forward-compatible issuer may add roles we don't know — we ignore them."""
    import jwt

    from api.settings import get_settings

    settings = get_settings()
    raw = jwt.encode(
        {"sub": "u1", "tier": "basic", "roles": ["pandit", "wizard"]},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    claims = decode_token(raw)
    assert claims.roles == {Role.PANDIT}


# ── Dual-role identity: the require_role gateway dependency ─────────────────────


def _role_app() -> FastAPI:
    app = FastAPI()

    @app.get("/provider")
    async def provider(
        claims: Annotated[TokenClaims, Depends(require_role(Role.PANDIT))],
    ) -> dict[str, list[str]]:
        return {"roles": sorted(r.value for r in claims.roles)}

    @app.get("/dual")
    async def dual(
        claims: Annotated[TokenClaims, Depends(require_role(Role.PATRON, Role.PANDIT))],
    ) -> dict[str, bool]:
        return {"ok": True}

    return app


@pytest.fixture
async def role_client():
    app = _role_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_pandit_role_passes_require_role(role_client: AsyncClient) -> None:
    token = create_token("pandit-1", roles=[Role.PANDIT])
    resp = await role_client.get("/provider", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "pandit" in resp.json()["roles"]


async def test_patron_only_rejected_with_tier_style_403(role_client: AsyncClient) -> None:
    """Patron-only JWT hits a pandit-gated route → 403 with the same detail shape
    ``require_tier`` uses (``detail.code`` + ``detail.message``)."""
    token = create_token("patron-1", roles=[Role.PATRON])
    resp = await role_client.get("/provider", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    body = resp.json()
    # Same envelope as require_tier's insufficient_tier response.
    assert set(body["detail"].keys()) == {"code", "message"}
    assert body["detail"]["code"] == "insufficient_role"
    assert "pandit" in body["detail"]["message"]


async def test_require_role_requires_all_listed_roles(role_client: AsyncClient) -> None:
    only_patron = create_token("p", roles=[Role.PATRON])
    dual = create_token("d", roles=[Role.PATRON, Role.PANDIT])
    r1 = await role_client.get("/dual", headers={"Authorization": f"Bearer {only_patron}"})
    r2 = await role_client.get("/dual", headers={"Authorization": f"Bearer {dual}"})
    assert r1.status_code == 403
    assert r2.status_code == 200


async def test_require_role_still_401_without_token(role_client: AsyncClient) -> None:
    resp = await role_client.get("/provider")
    assert resp.status_code == 401


# ── Vault references ───────────────────────────────────────────────────────────


@pytest.fixture
async def vault_session():
    """A fresh in-memory SQLite session with the vault tables created."""
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


async def test_write_returns_opaque_ref(vault_session) -> None:
    vault = Vault(vault_session)
    ref = await vault.write("123 Temple Street, Springfield", item_type=VaultItemType.EXACT_ADDRESS)
    assert isinstance(ref, VaultRef)
    assert ref.ref.startswith("vault_")
    # The opaque ref must not leak the raw value.
    assert "Temple Street" not in ref.ref
    assert "Springfield" not in ref.ref


async def test_read_roundtrips_and_is_access_logged(vault_session) -> None:
    vault = Vault(vault_session)
    ref = await vault.write("SSN-000-00-0000", item_type=VaultItemType.BACKGROUND_CHECK)

    # No reads yet → empty log.
    assert await vault.access_log(ref) == []

    value = await vault.read(ref, actor="admin-7", purpose="dispute-review")
    assert value == "SSN-000-00-0000"

    log = await vault.access_log(ref)
    assert len(log) == 1
    assert log[0]["actor"] == "admin-7"
    assert log[0]["purpose"] == "dispute-review"

    # A second read appends another audit row.
    await vault.read(ref, actor="system.kyc", purpose="reverify")
    assert len(await vault.access_log(ref)) == 2


async def test_read_unknown_ref_raises(vault_session) -> None:
    vault = Vault(vault_session)
    with pytest.raises(KeyError):
        await vault.read("vault_does_not_exist", actor="x")


async def test_tampered_entry_fails_integrity(vault_session) -> None:
    vault = Vault(vault_session)
    ref = await vault.write("secret-value", item_type=VaultItemType.OTHER)
    entry = await vault_session.get(VaultEntryRow, ref.ref)
    assert entry is not None
    # Flip a ciphertext byte → MAC check must fail.
    blob = bytearray(entry.sealed)
    blob[20] ^= 0x01
    entry.sealed = bytes(blob)
    await vault_session.flush()
    with pytest.raises(ValueError):
        await vault.read(ref, actor="x")


def test_vaultref_never_serializes_raw_value() -> None:
    """The core privacy guarantee: a VaultRef embedded in an API response model
    serializes to the opaque token only — the raw value is not reachable."""

    class BookingResponse(BaseModel):
        # Mirrors how bookings/verification records carry only a ref (F2 columns
        # address_ref / vault_refs), never the plaintext.
        address_ref: VaultRef

    ref = VaultRef(ref="vault_opaque_token_123")
    dumped = BookingResponse(address_ref=ref).model_dump()
    assert dumped == {"address_ref": {"ref": "vault_opaque_token_123"}}
    # There is no field or accessor on VaultRef that yields a raw address.
    assert not hasattr(ref, "value")
    assert not hasattr(ref, "raw")
    # str()/repr of the ref is the token, never a secret.
    assert str(ref) == "vault_opaque_token_123"
