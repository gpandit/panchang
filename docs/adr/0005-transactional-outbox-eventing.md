# ADR-0005: Start eventing with a transactional outbox

- **Status:** Accepted
- **Date:** 2026-10-07
- **Decision area:** Event publication and asynchronous work

## Context

Bookings, payments, webhooks, content publication, cache invalidation, reminder
fan-out, and user deletion need durable asynchronous side effects. Publishing
directly to a queue beside a database transaction can lose events or publish
state that later rolls back. A managed event bus would add operational and
schema cost before the domain contracts are stable.

## Decision

Every state-changing database transaction that requires asynchronous work writes
an outbox row in the same transaction as the source mutation. The row includes
an event ID, aggregate type and ID, event type, schema version, payload
reference, creation time, attempt/retry metadata, and processing state.

Redis/RQ-compatible workers claim and handle rows with at-least-once delivery.
Consumers must be idempotent using the event ID and their own durable effect or
idempotency record. Failures retry with bounded backoff and then enter an
observable dead-letter state for replay or operator resolution. Events are
append-only evidence for financial and booking transitions; a database row is
not considered asynchronously complete merely because a publish call returned.

The initial event envelope covers `panchang.recomputed`, `content.published`,
`user.location_changed`, `subscription.changed`, `booking.*`, `order.*`,
`payment.*`, `payout.*`, `dispute.*`, and `user.deleted`. A later EventBridge,
Kafka, or equivalent adapter may transport the same versioned envelope only
after contracts and operational evidence are stable; producers must not change
for that migration.

## Consequences

The database is the source of truth for publication intent and replay is
possible. Outbox growth, worker retries, duplicates, and dead letters require
metrics and operations. Consumers need careful idempotency design, but the
system avoids dual-write loss and premature event-bus coupling.

## Verification and gates

- S0 migration smoke tests insert and read a representative outbox row in a
  real PostgreSQL transaction.
- Tests prove rollback leaves no publishable outbox event and commit produces
  one durable event.
- Replay, duplicate delivery, retry, dead-letter, and consumer idempotency tests
  cover booking and payment flows before marketplace gates.

## References

- `docs/architecture-v3.0.md`, §6
- `docs/design-development-plan-v3.0.md`, §§2–3 and 6
- `docs/data-model-v3.0.md`, §§5 and 9
