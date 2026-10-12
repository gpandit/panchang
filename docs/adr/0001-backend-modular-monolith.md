# ADR-0001: Use a Python/FastAPI modular monolith first

- **Status:** Accepted
- **Date:** 2026-10-07
- **Decision area:** Backend architecture

## Context

The repository already has Python 3.12/FastAPI services, a Panchang
Computation Service (PCS), an API gateway, and SQLAlchemy/Alembic foundations.
The v3.0 plan needs clear domain ownership without paying the operational cost
of independently deployed services before usage and team boundaries are known.

## Decision

Build v3.0 as a modular monolith centered on the existing Python 3.12/FastAPI
repository. Keep domain modules separated by interfaces, repositories,
migrations, and event contracts. The public API is the versioned gateway;
`services/panchang` remains an internal PCS and `services/api` owns public
response shaping and orchestration.

The design must remain extraction-ready:

- domain code must not depend on HTTP loopback or another module's persistence;
- external systems are reached through ports/adapters;
- module-to-module asynchronous work uses the event envelope and outbox;
- a separate deployable is introduced only after measured scale, reliability,
  or ownership evidence and a superseding ADR.

This decision explicitly rejects introducing a parallel NestJS backend or
premature microservices for v3.0.

## Consequences

The team gets one deployment and one transaction boundary while contracts are
being reconciled. Module boundaries, forbidden imports, and integration tests
must compensate for the reduced process isolation. A later extraction may
require operational work, but the stable interfaces and events reduce that cost.

## Verification and gates

- `/v1` remains the only public API surface and OpenAPI is reconciled with the
  running FastAPI routes.
- Async SQLAlchemy repositories and Alembic migrations target PostgreSQL/PostGIS;
  SQLite is test-only and explicit.
- CI checks module boundaries, forbidden PCS imports, contract drift, and the
  S0 migration smoke test before S1 work is accepted.

## References

- `docs/architecture-v3.0.md`, §§1–4 and §9
- `docs/design-development-plan-v3.0.md`, §§2–3
- `docs/requirements-v3.0.md`, §1.1
