# ADR-0002: Retain native mobile clients

- **Status:** Accepted
- **Date:** 2026-10-07
- **Decision area:** Mobile architecture

## Context

The repository and v3.0 architecture identify native SwiftUI for iOS and
Kotlin/Jetpack Compose for Android. Mobile needs platform widgets, push,
background scheduling, and offline reading. A material migration would also
create a second contract and delay the accuracy-first delivery sequence.

## Decision

Retain the existing native SwiftUI and Kotlin/Compose direction for v3.0. Both
clients are thin consumers of the versioned FastAPI contract and use generated
or reconciled shared API types rather than independently authored authoritative
models.

Mobile may cache server-provided Panchang, festival, and calendar payloads for
offline reading. It must not compute or mutate authoritative Panchang values,
prices, commissions, taxes, entitlements, booking state, or payout state while
offline. A location change, cache miss, or expired entitlement requires a
server request before new authoritative output is shown.

Any migration to a cross-platform mobile stack, or material change to native
storage and synchronization, requires a new ADR with measured product,
accessibility, performance, and maintenance evidence.

## Consequences

Platform-specific code and release pipelines remain, but widgets, notifications,
and OS integration stay first-class. API reconciliation and cache invalidation
must be implemented twice, with the same contract tests and fixture payloads.

## Verification and gates

- iOS and Android consume the same versioned schemas and cannot import PCS or
  ephemeris code.
- Offline tests prove cached reads work and no new Panchang or money authority is
  synthesized.
- S2 client E2E tests cover web, iOS, and Android against the same API behavior.

## References

- `docs/architecture-v3.0.md`, §§2–3 and §9
- `docs/design-development-plan-v3.0.md`, §§3 and 5
- `docs/requirements-v3.0.md`, §§1.1, 3, and 4.2
