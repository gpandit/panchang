"""Transactional outbox and idempotency repository ports.

These repositories only persist event envelopes and opaque references.  They
do not publish events or run workers; those concerns belong to later stages.
The caller owns the SQLAlchemy transaction, matching :class:`api.db.Repository`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select, update

from api.db.repository import Repository
from api.db.v3_models import IdempotencyKeyRow, OutboxEventRow


class IdempotencyConflict(ValueError):
    """The same scoped key was submitted for a different request."""


@dataclass(frozen=True, slots=True)
class IdempotencyResult:
    record: IdempotencyKeyRow
    replayed: bool


def _now(value: datetime | None = None) -> datetime:
    return value or datetime.now(UTC)


class IdempotencyRepository(Repository[IdempotencyKeyRow]):
    """Persistence primitive for exactly-once command response replay."""

    model = IdempotencyKeyRow

    async def begin(
        self,
        *,
        scope: str,
        key: str,
        request_hash: str,
        expires_at: datetime | None = None,
    ) -> IdempotencyResult:
        existing = await self._find(scope=scope, key=key)
        if existing is not None:
            if existing.request_hash != request_hash:
                raise IdempotencyConflict("idempotency key was reused for a different request")
            return IdempotencyResult(existing, existing.state == "completed")

        record = IdempotencyKeyRow(
            id=str(uuid4()),
            scope=scope,
            key=key,
            request_hash=request_hash,
            state="pending",
            expires_at=expires_at,
        )
        await self.add(record)
        return IdempotencyResult(record, False)

    async def complete(
        self,
        record: IdempotencyKeyRow,
        *,
        response_ref: str,
        resource_ref: str | None = None,
        response_status: int = 200,
        completed_at: datetime | None = None,
    ) -> IdempotencyKeyRow:
        record.response_ref = response_ref
        record.resource_ref = resource_ref
        record.response_status = response_status
        record.state = "completed"
        record.completed_at = _now(completed_at)
        record.attempts += 1
        await self.session.flush()
        return record

    async def fail(self, record: IdempotencyKeyRow, *, error_ref: str) -> IdempotencyKeyRow:
        record.state = "failed"
        record.last_error = error_ref
        record.attempts += 1
        await self.session.flush()
        return record

    async def _find(self, *, scope: str, key: str) -> IdempotencyKeyRow | None:
        result = await self.session.execute(
            select(IdempotencyKeyRow).where(
                IdempotencyKeyRow.scope == scope,
                IdempotencyKeyRow.key == key,
            )
        )
        return result.scalar_one_or_none()


class OutboxRepository(Repository[OutboxEventRow]):
    """Claimable outbox rows; publication is intentionally outside this class."""

    model = OutboxEventRow

    async def enqueue(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload_ref: str,
        schema_version: int = 1,
        event_id: str | None = None,
        dedupe_key: str | None = None,
        idempotency_key_id: str | None = None,
        available_at: datetime | None = None,
    ) -> OutboxEventRow:
        if not isinstance(payload_ref, str) or not payload_ref.strip():
            raise ValueError("payload_ref must be a non-empty opaque reference")
        row = OutboxEventRow(
            id=event_id or str(uuid4()),
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            schema_version=schema_version,
            payload_ref=payload_ref,
            dedupe_key=dedupe_key,
            idempotency_key_id=idempotency_key_id,
            state="pending",
            available_at=available_at,
        )
        return await self.add(row)

    async def claim(
        self,
        *,
        worker_id: str,
        limit: int = 1,
        now: datetime | None = None,
    ) -> list[OutboxEventRow]:
        if limit < 1:
            return []
        claimed_at = _now(now)
        # FOR UPDATE/SKIP LOCKED is used where supported.  SQLite's explicit
        # fallback keeps local tests deterministic and uses the same state
        # predicate, while PostgreSQL provides the concurrency guarantee.
        statement = (
            select(OutboxEventRow)
            .where(
                OutboxEventRow.state.in_(("pending", "failed")),
                (OutboxEventRow.available_at.is_(None))
                | (OutboxEventRow.available_at <= claimed_at),
            )
            .order_by(OutboxEventRow.created_at, OutboxEventRow.id)
            .limit(limit)
        )
        if self.session.bind is not None and self.session.bind.dialect.name == "postgresql":
            statement = statement.with_for_update(skip_locked=True)
        rows = list((await self.session.execute(statement)).scalars().all())
        for row in rows:
            row.state = "claimed"
            row.claimed_by = worker_id
            row.claimed_at = claimed_at
            row.attempts += 1
        await self.session.flush()
        return rows

    async def mark_published(self, event_id: str, *, processed_at: datetime | None = None) -> bool:
        result = await self.session.execute(
            update(OutboxEventRow)
            .where(OutboxEventRow.id == event_id, OutboxEventRow.state == "claimed")
            .values(state="published", processed_at=_now(processed_at), last_error=None)
        )
        await self.session.flush()
        return result.rowcount == 1

    async def mark_failed(
        self,
        event_id: str,
        *,
        error_ref: str,
        retry_at: datetime | None = None,
        max_attempts: int = 10,
    ) -> bool:
        row = await self.session.get(OutboxEventRow, event_id)
        if row is None or row.state != "claimed":
            return False
        row.state = "dead_letter" if row.attempts >= max_attempts else "failed"
        row.last_error = error_ref
        row.available_at = retry_at or (_now() + timedelta(seconds=min(300, 2 ** min(row.attempts, 8))))
        row.claimed_by = None
        await self.session.flush()
        return True


__all__ = [
    "IdempotencyConflict",
    "IdempotencyRepository",
    "IdempotencyResult",
    "OutboxRepository",
]
