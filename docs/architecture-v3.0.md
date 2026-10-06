# The Pandit — Architecture Document

**Version:** 3.0 (canonical consolidated baseline)  
**Date:** 2026-10-07  
**Status:** Proposed build baseline; modular monolith first, extraction-ready boundaries  
**Paired documents:** `requirements-v3.0.md`, `data-model-v3.0.md`, `design-development-plan-v3.0.md`, `ai-prompts-v3.0.md`

## 1. Architectural north star

1. The Panchang Computation Service (PCS) is the only source of raw astronomical truth.
2. Panchang values are computed once, validated, stored, and served from a shared cache.
3. Clients render server payloads and cache them; they never calculate Panchang or authoritative
   money/business rules.
4. Festivals and religious guidance are versioned CMS/rule data, not code or date tables.
5. Sensitive data lives behind a separate Vault interface and is represented elsewhere only by
   opaque references.
6. Financial operations are server-authoritative, webhook-driven, idempotent, and auditable.
7. The current repository uses a Python/FastAPI modular monolith. Domain boundaries are modules,
   interfaces, migrations, and events first; independent deployables are a later optimisation.

## 2. System shape

```text
Web / iOS / Android / Admin / Provider-Seller portals
                         |
              Versioned FastAPI gateway (/v1)
        auth | RBAC | tier | rate-limit | response policy
                         |
  ----------------------------------------------------------------
  Panchang | Calendar | Festivals | Reminders | Users | CMS | PDF
  Muhurat  | AI      | Billing  | Commerce | Pandit | Pooja | Messaging
  ----------------------------------------------------------------
       PostgreSQL/PostGIS | Redis | RQ/outbox | S3-compatible storage
       Sensitive Vault | Swiss Ephemeris (PCS only) | external providers
```

The API gateway is the only public surface. The PCS is internal-only and can be called by the
gateway/cache warmer or an authenticated internal worker. During MVP, marketplace modules live
inside `services/api/src/api/marketplace/`; their interfaces must not depend on HTTP loopback.

## 3. Repository-aligned technology choices

| Concern | v3.0 choice |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic 2, SQLAlchemy async, Alembic |
| PCS | `services/panchang`, `pyswisseph`, deterministic pure computation plus cache adapter |
| Database | PostgreSQL + PostGIS in deployed environments; SQLite only for fast unit tests |
| Cache/queue | Redis; RQ-compatible workers; transactional outbox for durable event publication |
| Object storage | S3-compatible (MinIO locally) for PDFs/media/evidence |
| Web | Next.js App Router, TypeScript, Tailwind, existing design-token package |
| Admin/provider portals | React/TypeScript with named token references |
| Mobile | Existing native SwiftUI and Kotlin/Compose clients; decide any migration by ADR |
| Subscriptions | Apple IAP, Google Play Billing, Stripe Web, reconciled server-side |
| Service marketplace | Stripe Connect behind a provider interface |
| Goods marketplace | Shopify Storefront/Admin APIs and signed webhooks |
| AI | Provider-neutral LLM/embedding interfaces; retrieval boundary compatible with pgvector |
| Observability | Existing OpenTelemetry/Prometheus/Grafana scaffolding plus structured logs |
| Deployment | Docker Compose for local/staging-compatible use; provider-neutral production adapters |

## 4. Domain modules and ownership

### 4.1 PCS and calendar truth

`services/panchang` owns Swiss Ephemeris access, coordinate/timezone handling, anga derivation,
rise/set and derived windows, edge-case flags, and canonical `PanchangDay` serialization.
`services/api` owns cache lookup, calendar assembly, festival occurrences, reminders, and public
response shaping. No module outside PCS may import `swisseph`.

The cache key is:

```text
panchang:{date}:{grid_lat}:{grid_lon}:{iana_tz}:{ayanamsa}:{month_scheme}:{engine_version}
```

Default grid resolution is configurable at 0.1°. A cache entry is durable in PostgreSQL and fast
in Redis in production; past results are not expired without an engine-version decision. Cache
misses use a per-key distributed lock and write only validated results.

### 4.2 Platform modules

- **Users/Profile:** identity, locations, preferences, family membership, roles, account lifecycle.
- **Vault:** separate storage/access boundary for birth, KYC, background-check and exact-address
  payloads; callers receive references and scoped, audited reads.
- **Gateway/Entitlements:** JWT/OIDC validation, role and tier checks, rate limits, error envelope.
- **CMS:** versioned content/rules, source attribution, regional/locale fallback, moderation.
- **Billing:** subscription records and receipt reconciliation; never handles booking/goods money.
- **Calendar/PDF:** assembled views and queued signed exports.
- **Notifications:** event consumers, delivery preferences, quiet hours, retry/dead-letter state.

### 4.3 Commerce and marketplace modules

Commerce Core is shared by Pandit Services and Pooja Items. It owns provider accounts, KYC
adapters, commission configuration, ledger journals, escrow/holdback, refunds, payout scheduling,
disputes, standing, tax adapter, and reconciliation. It never owns marketplace-specific catalogue
or booking rules.

Pandit Services owns provider profiles, services, availability, search/ranking, quote inputs,
booking state machine, messaging, reviews, and marketplace admin workflows.

Pooja Items owns Shopify mapping, samagri-to-cart links, order mirrors, seller/fulfilment views,
and the Shopify webhook pipeline. Shopify is authoritative for product price, inventory, checkout,
shipping, and goods tax.

## 5. Canonical contracts

### 5.1 PanchangDay interval

Every interval includes `startUtc`, `endUtc`, `localOffsetMinutes`, `hoursFromSunrise`, and
`flags`. Display strings (12-hour, 24-hour, 24-plus) are derived at the edge. The UTC instant is
the identity; local text is not used for comparisons.

### 5.2 Festival rule

Rules are JSON with `id`, `type`, `scheme`, month/paksha/tithi or solar/nakshatra criteria,
anchor, regional overrides, priority, and tie-break. The resolver emits occurrences with rule
version, location grid, year, anchor instant, and explanation. Published rules are immutable by
version; corrections create a new version and invalidate dependent cache entries.

### 5.3 Quote and booking

Quotes are generated server-side from service, travel, samagri, platform fee, tax, currency, and
policy configuration. The booking stores the complete quote and cancellation policy snapshot.
Money amounts use integer minor units and ISO currency; clients submit selections, never totals.

Booking state transitions are explicit, authorised by role, stored with an append-only event, and
published through the outbox after commit. DB constraints and row/range locking prevent overlap.

### 5.4 Errors and versioning

All public endpoints use `/v1`. Breaking changes require `/v2`; compatible additions are allowed
within v1. Errors use `{error:{code,message,details,retry,documentation_url}}`. External dependency
failures use circuit breakers and actionable retry metadata.

## 6. Persistence and eventing

PostgreSQL is authoritative for user data, CMS, rules, subscriptions, bookings, ledger journals,
and order mirrors. Redis is a performance and coordination layer, never the sole store for money,
bookings, or user-owned data. Sensitive Vault storage has separate credentials and audit policy.

Every state-changing transaction that needs asynchronous work writes an outbox row containing an
event id, aggregate type/id, event type, schema version, payload reference, and retry metadata.
Workers claim rows idempotently, publish/handle them, and record attempts. A later deployment may
route the same event envelope to EventBridge/Kafka without changing domain producers.

Required event families include `panchang.recomputed`, `content.published`, `user.location_changed`,
`subscription.changed`, `booking.*`, `order.*`, `payment.*`, `payout.*`, `dispute.*`, and
`user.deleted`.

## 7. Security and privacy

- OIDC/email/OTP tokens are short-lived with refresh rotation; roles are checked server-side.
- Vault values are encrypted with envelope keys, access-logged with purpose, and never included in
  analytics, logs, prompts, ordinary exports, or broad ORM models.
- Exact ceremony addresses are time-scoped and disclosed only after paid confirmation.
- Webhooks verify signatures and idempotency before state mutation; no raw card data is stored.
- Admin content, configuration, moderation, finance, and KYC actions have actor/audit records.
- Account deletion/export follows a tested cascade across profiles, notes, family, bookings,
  messages, orders, vault data, and derived analytics identifiers.

## 8. Performance, reliability, and operations

- Cached Panchang day p95 ≤2s; search typical ≤1s; monthly API availability target 99.9%.
- Warm popular locations for ≥15 months and pre-warm ahead of major festivals.
- Queue PDFs, reminder fan-out, webhook processing, payouts, reconciliation, and AI indexing.
- Alert on cache misses, compute failures, queue backlog, webhook gaps, payment failures, ledger
  variance, stuck payouts, disputes, and privacy/audit failures.
- PostgreSQL WAL/daily backups target RPO ≤1 hour and RTO ≤4 hours. Cache can be recomputed.
- CI blocks merges on tests, accuracy, forbidden imports, contract drift, and launch-readiness.

## 9. Architecture decisions to keep visible

1. Python/FastAPI modular monolith now; extraction only after measured need.
2. 0.1° configurable cache grid plus IANA timezone.
3. ±2/±5 executable accuracy tolerances; ±1 is a target, not an untested claim.
4. Transactional outbox before managed event bus.
5. In-person marketplace first; live video and complex group flows later.
6. Provider interfaces for KYC, video, Shopify, LLM, embeddings, and tax.
7. Named design tokens only; no agent-authored visual system.
