"""Focused S0-05 contract tests for replay safety and sensitive-data boundaries."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from api.db import Base
from api.db import models as _models  # noqa: F401
from api.db.v3_models import OutboxEventRow
from api.outbox import IdempotencyRepository, OutboxRepository
from api.vault import InMemoryVault, InMemoryVaultAccessLog, VaultAccessDenied


def test_outbox_event_id_and_dedupe_key_are_unique() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            session.add_all(
                [
                    OutboxEventRow(
                        id="event-1",
                        aggregate_type="booking",
                        aggregate_id="booking-1",
                        event_type="booking.requested",
                        payload_ref="object://event-1",
                    ),
                    OutboxEventRow(
                        id="event-1",
                        aggregate_type="booking",
                        aggregate_id="booking-2",
                        event_type="booking.requested",
                        payload_ref="object://event-2",
                    ),
                ]
            )
            with pytest.raises(IntegrityError):
                session.commit()
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.mark.asyncio
async def test_outbox_claimability_and_idempotency_replay() -> None:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        outbox = OutboxRepository(session)
        event = await outbox.enqueue(
            aggregate_type="booking",
            aggregate_id="booking-1",
            event_type="booking.requested",
            payload_ref="object://event-1",
        )
        claimed = await outbox.claim(worker_id="worker-a", now=datetime.now(UTC))
        assert [row.id for row in claimed] == [event.id]
        assert claimed[0].state == "claimed"
        assert await outbox.mark_published(event.id)

        idempotency = IdempotencyRepository(session)
        first = await idempotency.begin(scope="booking:create", key="request-1", request_hash="hash-a")
        assert not first.replayed
        await idempotency.complete(first.record, response_ref="object://response-1", response_status=201)
        replay = await idempotency.begin(scope="booking:create", key="request-1", request_hash="hash-a")
        assert replay.replayed
        assert replay.record.response_ref == "object://response-1"
        await session.commit()
    await engine.dispose()


def test_vault_returns_opaque_reference_and_audits_scoped_reads() -> None:
    audit = InMemoryVaultAccessLog()
    vault = InMemoryVault(access_log=audit)
    raw = {"date_of_birth": "1990-01-01", "address": "sensitive"}
    reference = vault.put(
        raw,
        subject_type="user",
        subject_id="user-1",
        region="us",
        purpose="booking.address",
    )
    assert "sensitive" not in repr(reference)
    assert "date_of_birth" not in str(reference.as_dict())
    assert vault.read(reference, actor_ref="pandit-1", purpose="booking.address", subject_id="user-1") == raw
    assert audit.records[0].actor_ref == "pandit-1"
    assert audit.records[0].purpose == "booking.address"
    with pytest.raises(VaultAccessDenied):
        vault.read(reference, actor_ref="pandit-1", purpose="unrelated")
    assert all(not hasattr(record, "value") for record in audit.records)


def test_ordinary_outbox_shape_has_reference_not_raw_payload() -> None:
    columns = set(OutboxEventRow.__table__.columns.keys())
    assert "payload_ref" in columns
    assert "payload" not in columns
    assert "sensitive" not in repr(OutboxEventRow)
