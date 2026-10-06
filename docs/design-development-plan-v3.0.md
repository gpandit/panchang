# The Pandit — Design & Development Plan

**Version:** 3.0 (canonical implementation plan)  
**Date:** 2026-10-07  
**Strategy:** accuracy-first, API-first, web-first, incremental modular delivery  
**Primary implementation stack:** Python/FastAPI repository baseline; see `architecture-v3.0.md`.

**Build overview:** [`../build-dashboard.html`](../build-dashboard.html) inventories the S0–S7
work packages, their v3.0 disposition (complete, needs update, or yet to develop), and source
evidence as assessed on 2026-10-07. It is a static snapshot, not a live CI/status feed.

## 1. Delivery rules

1. Work from the stages below in order. Parallel work is allowed only after the named contract and
   gate exists.
2. Every unit of work changes code, tests, migrations/OpenAPI when applicable, and a changelog or
   status entry. “Implemented” is not a substitute for gate evidence.
3. Freeze a contract before building multiple clients. Use mocks generated from the contract, not
   hand-authored divergent types.
4. Do not add marketplace UI until the persistence, Vault, quote, booking, and money contracts are
   stable. Do not call the current prototype complete because a route returns an HTTP 200.
5. Agents must use the existing design-token names and may not invent visual design.

## 2. Stage map and gates

| Stage | Scope | Exit gate |
|---|---|---|
| S0 | ADRs, repository contracts, migrations, CI, outbox, OpenAPI reconciliation | ADRs accepted; checks green; migration smoke test |
| S1 | PCS, cache, warmer, rule DSL, accuracy harness | ≥500 references/≥10 locations; executable harness green |
| S2 | Auth/profile/Vault, calendar, festivals, notes, reminders, CMS, subscriptions, PDF | 3-client E2E; cached day p95 ≤2s; no sensitive leakage |
| S3 | Commerce Core, Stripe Connect adapter, ledger, tax, refunds, payouts, disputes | Sandbox money scenarios pass; journals balance; reconciliation zero |
| S4 | Pandit marketplace, in-person booking, messaging, reviews, ops | 50 concurrent slot requests → exactly one; policy snapshot and ops console proven |
| S5 | Shopify catalog/cart/checkout, seller overlay, order ingest and splits | signed webhook → order → ledger → payout trace complete |
| S6 | AI/RAG, full Tithi reminders, muhurat, life planner, video, widgets, HD PDF | SLOs and privacy/compliance tests; video success target when enabled |
| S7 | hardening, licensing, security, store/legal, DR/runbooks | commercial Swiss Ephemeris licence and compliance sign-off |

## 3. S0 — foundations and contract reconciliation

**Deliverables**

- Record ADRs for backend choice (Python/FastAPI is the current choice), mobile, cache grid,
  accuracy tolerances, eventing, KYC, video, commission/pass-through, cancellation, holdback,
  data residency, and AI retention.
- Reconcile `docs/Conversation/the-pandit-openapi-v1.yaml` with the running FastAPI surface. Mark
  unimplemented paths as planned instead of exposing them as working.
- Establish SQLAlchemy async session/repository conventions and an Alembic migration path for
  PostgreSQL/PostGIS. Keep SQLite tests explicit and add a real Postgres integration job.
- Add the Data Model v3 tables in dependency order, the transactional outbox, idempotency keys,
  and a Vault interface with a test fake.
- Add forbidden-import and client-authority checks: only PCS may import `swisseph`; clients may not
  compute Panchang or authoritative prices.

**Done when:** a fresh checkout can migrate, insert/read a representative user and outbox row,
generate/validate OpenAPI, and run the existing checks without relying on a hidden local service.

## 4. S1 — Panchang truth

**Work packages:**

1. Encapsulate all ephemeris calls behind PCS; separate calendar approximation code from the
   production contract and document any remaining calibration gap.
2. Produce the canonical interval schema with UTC, local offset, `hoursFromSunrise`, and flags.
3. Implement high-latitude fallback as a named, explicit approximation with a `sunriseFallback`
   flag; never return an unmarked synthetic sunrise.
4. Wire Redis/PostgreSQL cache adapters, 0.1° grid configuration, IANA timezone keying, locks,
   engine-version invalidation, and a ≥15-month warmer.
5. Load the festival-rule JSON through versioned CMS/rule data and resolve major festivals plus
   recurring cycles.
6. Expand the independent reference set to ≥500 days/≥10 locations, including DST, polar-edge,
   Adhika, Kshaya, Vriddhi, both schemes, and major festivals.

**Tests:** property tests for angle/span monotonicity and lunations; reference harness; cache-key
and lock tests; edge-case snapshots. Current four-fixture data is not a gate-passing dataset.

## 5. S2 — core product

Build in dependency order:

1. Identity, roles, preferences, locations, Vault refs, export/delete, and gateway tier checks.
2. Calendar assembly from cache, then web day/month/week/year/range views and offline read caches.
3. CMS workflow, rule administration, published festival pages, regional fallback, flag/review.
4. Persistent notes/bookmarks/reminders and the Gregorian scheduler; freeze the Tithi/Nakshatra
   recurrence contract here. The full kshaya/vriddhi resolver and location re-resolution gate in S6.
5. Subscription receipt adapters and entitlement reconciliation; never trust client tier claims.
6. Queue-backed PDF jobs, object storage, signed URLs, share/export/integration endpoints.
7. Admin content, reporting, audit and rate-limit surfaces.

**Client rule:** retain the existing web, iOS, Android, admin, and design-token structure where it
meets these contracts. Reconcile stale routes and generated types before adding screens.

## 6. S3 — Commerce Core

Implement the shared money spine before marketplace features:

- provider accounts and pluggable KYC/Vault adapter;
- integer-minor-unit quote/commission/tax policies and immutable snapshots;
- Stripe Connect test-mode PaymentIntent authorisation/capture, holdback, refunds and transfers;
- append-only double-entry ledger and nightly/hourly reconciliation;
- idempotent signed webhooks, outbox consumers, retry/dead-letter queues;
- dispute lifecycle that freezes payout, evidence references, and finance/admin views;
- multi-currency display with settlement limitations clearly surfaced.

Test each documented money scenario with Stripe test clocks/fakes, replayed webhooks, failed
transfers, partial refunds, cancellation tiers, tax errors, and ledger-zero assertions.

## 7. S4 — Pandit Services MVP

### Provider track

Onboarding/agreements → KYC status → operations approval → service catalogue → travel policy →
availability/blackouts/lead time/buffer → provider dashboard.

### Patron track

Search/profile → availability → quote → Silver/Gold entitlement → address Vault ref → payment
authorisation → booking state machine → messaging/notifications → completion/review.

### Required correctness tests

- database-level no-overlap constraint and 50 concurrent requests;
- manual-accept timeout releases authorisation and slot;
- address is absent before confirmation and inaccessible after completion;
- quote and cancellation policy are immutable snapshots;
- Pandit cancellation fully refunds and affects standing;
- dispute prevents payout;
- Basic checkout returns 403 with an upgrade action;
- all transitions produce exactly one auditable event and idempotent side effects.

## 8. S5 — Pooja Items MVP

Implement Shopify interfaces with a fake and signed webhook fixtures before production credentials:
catalogue/search → samagri mapping → cart → Shopify-hosted checkout → paid/fulfilled/refunded
webhooks → order mirror/seller splits → Commerce Core ledger/payout. Never store a copied price as
the authority. Add seller approval, fulfilment write-back, returns, product reviews, and admin
reconciliation after the happy path is reliable.

## 9. S6 — deferred intelligence and experience

Only after S1–S5 gates: provider-neutral RAG, source citations and retention controls; advanced
muhurat and life planner; full Tithi reminders; optional LiveKit/video adapter with consented
recording off by default; family conflict UX; widgets; advanced ranking; group/gift bookings; HD
branded calendars; temple/community features.

## 10. S7 — launch hardening

Complete commercial Swiss Ephemeris licensing, dependency and secret scans, penetration/privacy
review, data-residency/legal review, App Store/Play payment review, tax/finance configuration,
backups/restore drill, rate-limit/load tests, observability dashboards, incident and reconciliation
runbooks, and a canary deployment. A build with `SWISSEPH_LICENSE_MODE` not set to the approved
commercial mode cannot be promoted.

## 11. Current codebase status at v3.0 baseline

The repository is a reusable prototype/foundation, not a complete implementation. Existing useful
areas are the PCS structure and edge-case tests, gateway/rate-limit/auth patterns, SQLAlchemy/Alembic
foundation, admin/CMS/audit patterns, PDF queue interface, web calendar/today flows, native mobile
cache/repository patterns, design-token generator, local Compose observability, and launch checks.

Known blockers before S2/S3: only temple tables are migrated; API persistence/cache paths are partly
in-memory; notes/reminders/profile include stubs/501s; festival resolution is incomplete; shared
client types are hand-authored; mobile routes and gateway routes diverge; real Postgres/Redis
integration coverage is missing; marketplace, Vault, ledger, booking, tax, Shopify and KYC modules
are absent. Use this as a migration backlog, not as a reason to delete the repository.

## 12. Check commands and evidence

Run from repository root unless noted:

```sh
pnpm run ci:lint
pnpm run ci:typecheck
pnpm run ci:test
pnpm run ci:format:check
uv run python tools/accuracy_harness/run.py
uv run python tools/check_launch_readiness.py
```

For changed client packages also run the package's Vitest/Next checks; for database work run a
PostgreSQL migration/integration job. Record actual command, working directory, exit status, and
known gaps in `docs/BUILD-STATUS.md`.

## 13. Work-item template

```text
ID / stage / track:
Goal and user-visible result:
Requirements and model sections:
Contracts to implement/consume:
Dependencies and forbidden changes:
Acceptance tests and gate evidence:
Files/migrations/OpenAPI/changelog expected:
Rollback or data-migration plan:
```
