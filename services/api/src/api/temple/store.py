"""Temple store — temple configs + temple-admin accounts, persisted to Postgres.

Backed by SQLAlchemy (``api.db``). The public function names/signatures are unchanged
from the original in-memory version, so the routers call it exactly as before; only
the storage moved from process-local dicts to the database.

A temple-admin account binds an email/password to exactly one ``temple_id``. Schema is
owned by Alembic; ``seed()`` inserts the demo temple + admin and is idempotent.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from api.auth import hash_password
from api.db import Base, get_engine, session_scope
from api.db.models import TempleAdminRow, TempleRow
from api.models.temple import (
    AartiEntry,
    TempleAdminAccount,
    TempleConfig,
    TempleConfigIn,
    TempleEvent,
    TempleLocation,
)

# Stable id for the demo temple so the Display has a default target.
DEMO_TEMPLE_ID = "temple-siddhivinayak"
DEMO_ADMIN_EMAIL = "admin@siddhivinayak.temple"
DEMO_ADMIN_PASSWORD = "templeadmin"  # demo seed credential only


def _now() -> datetime:
    return datetime.now(UTC)


# ── Row ↔ model mapping ───────────────────────────────────────────────────────


def _to_config(row: TempleRow) -> TempleConfig:
    return TempleConfig(
        id=row.id,
        name=row.name,
        name_dev=row.name_dev,
        tagline=row.tagline,
        location=TempleLocation(**row.location),
        aarti=[AartiEntry(**a) for a in row.aarti],
        events=[TempleEvent(**e) for e in row.events],
        updated_at=row.updated_at,
        updated_by=row.updated_by,
    )


def _to_account(row: TempleAdminRow) -> TempleAdminAccount:
    return TempleAdminAccount(
        id=row.id,
        email=row.email,
        password_hash=row.password_hash,
        salt=row.salt,
        temple_id=row.temple_id,
        created_at=row.created_at,
    )


# ── Temples ──────────────────────────────────────────────────────────────────


def get_temple(temple_id: str) -> TempleConfig | None:
    with session_scope() as s:
        row = s.get(TempleRow, temple_id)
        return _to_config(row) if row else None


def list_temples() -> list[TempleConfig]:
    with session_scope() as s:
        rows = s.execute(select(TempleRow).order_by(TempleRow.name)).scalars().all()
        return [_to_config(r) for r in rows]


def create_temple(
    *,
    name: str,
    name_dev: str,
    tagline: str,
    location: TempleLocation,
    aarti: list[AartiEntry],
    events: list[TempleEvent],
    actor_id: str | None,
    temple_id: str | None = None,
) -> TempleConfig:
    tid = temple_id or f"temple-{uuid.uuid4().hex[:8]}"
    with session_scope() as s:
        row = TempleRow(
            id=tid,
            name=name,
            name_dev=name_dev,
            tagline=tagline,
            location=location.model_dump(),
            aarti=[a.model_dump() for a in aarti],
            events=[e.model_dump() for e in events],
            updated_at=_now(),
            updated_by=actor_id,
        )
        s.add(row)
        s.flush()
        return _to_config(row)


def update_temple(
    temple_id: str, data: TempleConfigIn, *, actor_id: str | None
) -> TempleConfig | None:
    """Update the editable subset (location, aarti, events). Identity is preserved."""
    with session_scope() as s:
        row = s.get(TempleRow, temple_id)
        if row is None:
            return None
        row.location = data.location.model_dump()
        row.aarti = [a.model_dump() for a in data.aarti]
        row.events = [e.model_dump() for e in data.events]
        row.updated_at = _now()
        row.updated_by = actor_id
        s.flush()
        return _to_config(row)


# ── Accounts ─────────────────────────────────────────────────────────────────


def get_account_by_email(email: str) -> TempleAdminAccount | None:
    email_norm = email.strip().lower()
    with session_scope() as s:
        row = s.execute(
            select(TempleAdminRow).where(TempleAdminRow.email == email_norm)
        ).scalar_one_or_none()
        return _to_account(row) if row else None


def assign_admin(*, email: str, password: str, temple_id: str) -> TempleAdminAccount:
    """Create (or replace) an admin login bound to a temple."""
    email_norm = email.strip().lower()
    password_hash, salt = hash_password(password)
    with session_scope() as s:
        row = s.execute(
            select(TempleAdminRow).where(TempleAdminRow.email == email_norm)
        ).scalar_one_or_none()
        if row is None:
            row = TempleAdminRow(
                id=f"tadmin-{uuid.uuid4().hex[:8]}",
                email=email_norm,
                password_hash=password_hash,
                salt=salt,
                temple_id=temple_id,
                created_at=_now(),
            )
            s.add(row)
        else:
            # Re-assigning updates the credential/binding in place.
            row.password_hash = password_hash
            row.salt = salt
            row.temple_id = temple_id
        s.flush()
        return _to_account(row)


# ── Lifecycle ────────────────────────────────────────────────────────────────


def clear() -> None:
    """Drop and recreate all tables — used by the test suite only."""
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def _demo_aarti() -> list[AartiEntry]:
    """Ported from the hardcoded AARTI.schedule in the Temple Display screen."""
    return [
        AartiEntry(
            key="mangala", name="Maṅgala Ārati", dev="मंगला आरती", time="05:00", note="Awakening"
        ),
        AartiEntry(
            key="shringar", name="Śṛṅgāra Ārati", dev="शृंगार आरती", time="08:30", note="Adornment"
        ),
        AartiEntry(
            key="rajbhog",
            name="Rājbhoga Ārati",
            dev="राजभोग आरती",
            time="12:00",
            note="Midday bhoga",
        ),
        AartiEntry(key="sandhya", name="Sandhyā Ārati", dev="संध्या आरती", time="19:00", note="Dusk"),
        AartiEntry(key="shayan", name="Śayana Ārati", dev="शयन आरती", time="20:45", note="Rest"),
    ]


def seed() -> None:
    """Seed one demo temple + admin so the app is usable immediately. Idempotent."""
    if get_temple(DEMO_TEMPLE_ID) is not None:
        return
    create_temple(
        temple_id=DEMO_TEMPLE_ID,
        name="Shree Siddhivinayak Mandir",
        name_dev="श्री सिद्धिविनायक मंदिर",
        tagline="Sanātana Dharma",
        location=TempleLocation(
            label="Dubai · United Arab Emirates",
            lat=25.2048,
            lon=55.2708,
            tz="Asia/Dubai",
        ),
        aarti=_demo_aarti(),
        events=[
            TempleEvent(
                id="evt-sankashti",
                title="Sankashti Chaturthi",
                title_dev="संकष्टी चतुर्थी",
                date="2026-06-08",
                description="Special Ganesha abhishekam after Sandhyā Ārati.",
            ),
        ],
        actor_id="system",
    )
    assign_admin(email=DEMO_ADMIN_EMAIL, password=DEMO_ADMIN_PASSWORD, temple_id=DEMO_TEMPLE_ID)
