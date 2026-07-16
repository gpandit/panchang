# Development Plan — "Book a Pandit" Pandit Services Marketplace

**Implements:** Requirements Addendum A · **Architecture:** `docs/architecture-marketplace.md` (v1.2)
**Reads with:** Requirement Specifications v2.0 · Development Plan v1.1
**Target:** hand each step (or step group) directly to Claude Code.
**Date:** June 2026

---

## How to use this plan

- Work is grouped into **workstreams** (`F`, `A`–`G`). Within a workstream, steps are mostly serial.
- The **Parallelization map** (below) shows which workstreams/steps can run **in parallel** once
  their dependencies are met. Steps marked **∥** are safe to run concurrently with their siblings.
- Each step is a self-contained unit with: **Goal**, **Build** (paths in the monorepo), **Depends
  on**, and **Done when** (acceptance criteria). Hand a single step ID to Claude Code, e.g.
  *"Build step F1 from `docs/dev-plan-marketplace.md`."*
- **Monorepo map:** backend modules → `services/api/src/api/marketplace/<module>/`; routers →
  `services/api/src/api/routers/v1/marketplace/` and `.../routers/admin/`; Pydantic models →
  `services/api/src/api/models/marketplace.py`; migrations → `services/api/migrations/` (Alembic);
  web → `apps/web`; admin → `apps/admin`; mobile → `apps/ios`, `apps/android`; shared TS client →
  `packages/api-client-ts`.
- **MVP target = Addendum A §A18.1** (in-person first; live video fast-follows). Phase-2/3 steps are
  marked **[P2]** / **[P3]**.

---

## Model assignment (quota-aware — Pro plan)

To stretch Pro quota without extra spend, each step is tagged with the model to run it on. The
policy:

- **🔴 Opus** — steps where a wrong design **compounds downstream**: the persistence/schema spine,
  anything touching **money** (escrow, commission, refunds, tax, server-authoritative quote),
  **security/identity** (dual-role, Vault, KYC), and **correctness-critical logic** (booking state
  machine, no-double-booking, ranking algorithm, dispute/payout freeze, provider standing).
- **🟢 Sonnet** — **mechanical, well-specified** work: CRUD endpoints, read/dashboard APIs,
  scaffolding, data seeds, notification templates, messaging plumbing, **all admin consoles**, and
  **all client screens** (web + mobile).

Run the 🔴 Opus steps deliberately (and review them); let the 🟢 Sonnet steps run loose. When
handing a step to a subagent, set its model accordingly (`model: opus` / `model: sonnet`).

| Step | Model | Why |
|---|---|---|
| F1 Persistence layer | 🔴 Opus | Pattern every module inherits |
| F2 Schema + no-double-booking constraint | 🔴 Opus | Integrity-critical |
| F3 Dual-role identity + Vault | 🔴 Opus | Security / PII |
| F4 Module skeleton + routers | 🟢 Sonnet | Scaffolding |
| F5 Taxonomy seed | 🟢 Sonnet | Data fixture |
| A1 Provider onboarding flow | 🟢 Sonnet | Simple state + CRUD |
| A2 Verification & KYC | 🔴 Opus | Security, Vault, webhooks |
| A3 Catalogue / travel / samagri / pricing | 🟢 Sonnet | CRUD + validation |
| A4 Availability & scheduling | 🔴 Opus | Scheduling correctness (ties to F2 constraint) |
| A5 Provider dashboard | 🟢 Sonnet | Read aggregation |
| B1 Discovery & search | 🟢 Sonnet | Filters/sort (ranking stub → D3) |
| B2 Pandit profile view | 🟢 Sonnet | Read assembly |
| B3 Booking flow + Quote contract | 🔴 Opus | Server-authoritative pricing — the pivot |
| B4 Manage / reschedule / cancel / recurring | 🟢 Sonnet | Wires to C1/C4 |
| C1 Booking lifecycle state machine | 🔴 Opus | Correctness-critical |
| C2 Stripe Connect escrow / payouts / webhooks | 🔴 Opus | Money |
| C3 Commission & fee engine | 🔴 Opus | Money |
| C4 Cancellation / refund / no-show engine | 🔴 Opus | Money + policy snapshot |
| C5 Tax & multi-currency | 🔴 Opus | Tax correctness (display glue is Sonnet-ok) |
| D1 Messaging + PII masking | 🟢 Sonnet | Plumbing (review leakage heuristics) |
| D2 Notifications | 🟢 Sonnet | Templates / triggers |
| D3 Reviews & ranking | 🔴 Opus | Ranking algorithm + double-blind reveal |
| D4 Trust, safety & disputes | 🔴 Opus | Security + payout freeze + standing |
| D5 Live video **[P2]** | 🟢 Sonnet | SDK integration glue |
| E1–E6 Admin consoles | 🟢 Sonnet | Consoles |
| G-W*, G-M* Clients (web + mobile) | 🟢 Sonnet | UI |
| X5 Observability wiring | 🟢 Sonnet | Config / dashboards |
| X1–X4, X6 Vendor / legal / compliance / licence | — | Human / ops, not code-gen |

**Tally:** 10 Opus steps (the spine + all money/security/correctness), ~15+ Sonnet steps (everything
mechanical). Track per-step status in [`docs/BUILD-STATUS.md`](BUILD-STATUS.md).

---

## Parallelization map (the short version)

```
WS-F  Foundation (mostly SERIAL — everything depends on it)
        F1 → F2 → F3 → F4 → F5
                         │
        ┌────────────────┼───────────────┬────────────────┬───────────────┐
        ▼                ▼                ▼                ▼               ▼
   WS-A Provider    WS-C Money &     WS-D Comms &     WS-E Admin     WS-G Clients
   (pandit side)    Lifecycle        Trust            & Ops          (web→mobile)
        ∥                ∥                ∥                ∥               ∥
   WS-B Patron      (C depends on F + B3 quote)   (D, E read each domain's API)
   (customer side)
```

- **WS-F must finish first** (persistence, data model, dual-role identity, module skeleton, taxonomy).
- After F: **WS-A (Provider)** and **WS-B (Patron discovery/profile)** run **fully in parallel**.
- **WS-C (Money & Lifecycle)** starts once the Booking entity + quote shape exist (F2 + B3 contract);
  C1 (state machine) and C2 (Stripe) can be built in parallel by two agents.
- **WS-D (Comms/Trust)** and **WS-E (Admin/Ops)** run in parallel with A/B/C — each consumes the
  domain APIs as they land; build against the API contracts, integrate as endpoints go live.
- **WS-G (Clients):** web leads; iOS/Android run in parallel with web once the API contract for a
  flow is frozen. Use `packages/api-client-ts` as the contract source of truth.
- **Legal/compliance (WS-X)** and **Stripe/KYC/Video vendor setup** run **continuously** alongside
  everything and gate launch, not earlier steps.

---

## WS-F · Foundation (serial — do first)

### F1 — Persistence layer (Postgres + SQLAlchemy async + Alembic)
- **Goal:** stand up a real relational layer; the marketplace cannot use in-memory dict stores.
- **Build:** add `sqlalchemy[asyncio]>=2`, `alembic`, `asyncpg` to `services/api/pyproject.toml`;
  create `api/db/` (async engine + session factory + base + `get_session` FastAPI dependency);
  initialise Alembic in `services/api/migrations/`; add Postgres to `infra/docker-compose.yml`
  (already referenced in `settings.py`). Establish a thin **repository pattern** (`api/db/repository.py`).
- **Depends on:** —
- **Done when:** `alembic upgrade head` runs in CI and locally; a smoke test inserts/reads a row via
  an async session; existing tests still green.

### F2 — Marketplace schema + migrations
- **Goal:** create all marketplace tables from the data model (Architecture §3 / Addendum A §A13).
- **Build:** SQLAlchemy models for Pandit, PanditService, ServiceType, TravelPolicy, Availability,
  Booking, BookingEvent, Payment, Payout, Refund, Review, Conversation, Message, VideoSession,
  Dispute, VerificationRecord; Pydantic schemas in `api/models/marketplace.py`. Add the
  **no-double-booking constraint** (partial unique / exclusion on `(pandit_id, time-range)` for
  active states) and `Booking.policySnapshot` (JSONB). Alembic migration.
- **Depends on:** F1
- **Done when:** migration creates every table + the overlap constraint; a test proves two
  overlapping confirmed bookings for one pandit are rejected at the DB level.

### F3 — Dual-role identity + Vault references
- **Goal:** one login can hold a Patron and/or Pandit role; sensitive refs go to the Vault.
- **Build:** extend the user model/JWT claims to carry roles (`patron`, `pandit`); a
  `require_role(...)` gateway dependency mirroring `require_tier` in `api/dependencies.py`. Add a
  `VaultRef` abstraction (`api/marketplace/vault.py`) — store-by-reference for ID docs / bg-check /
  exact addresses, access-logged, never serialized to clients.
- **Depends on:** F1, F2
- **Done when:** a JWT with `pandit` role passes `require_role(Role.PANDIT)`; a vault write returns a
  ref and the raw value is provably absent from any API response model.

### F4 — Marketplace module skeleton + router registration
- **Goal:** wire the empty domain modules and the `/v1/marketplace` + admin router prefixes.
- **Build:** create `api/marketplace/<module>/` packages per Architecture §1; register routers in
  `api/main.py` under `/v1` and `/admin/v1`; add a `/v1/marketplace/healthz`. Update
  `packages/api-client-ts` generation to include the new OpenAPI paths.
- **Depends on:** F1
- **Done when:** `GET /v1/marketplace/healthz` returns 200; OpenAPI shows the new tags; `pnpm`
  client regen succeeds.

### F5 — Service taxonomy seed
- **Goal:** the admin-curated `ServiceType` catalogue exists and links to festival/muhurat ids.
- **Build:** seed migration/fixture for ServiceTypes (festival officiation reusing §5.5 festival
  ids; pujas/ceremonies aligned to §5.6.1 muhurat event types; optional astrology/consultation);
  taxonomy tags. Admin CRUD comes in WS-E (E2).
- **Depends on:** F2
- **Done when:** seeded ServiceTypes are queryable and each carries an optional `festivalRef` /
  `muhuratEventRef`.

---

## WS-A · Provider (Pandit) side — **∥ with WS-B after F**

### A1 — Provider registration & onboarding flow
- **Goal:** a pandit creates a provider account, accepts agreements, and submits for review.
- **Build:** `api/marketplace/providers/` — endpoints to create/upgrade a user to pandit role,
  record agreement/code-of-conduct/cancellation-policy acceptance (versioned + logged), and a
  `submit_for_review` transition. Onboarding state machine: `DRAFT → SUBMITTED → APPROVED |
  REJECTED | CHANGES_REQUESTED`. **Hard gate:** not discoverable until `APPROVED + VERIFIED`.
- **Depends on:** F3, F4
- **Done when:** an unapproved pandit never appears in search; agreement acceptances are logged.

### A2 — Verification & KYC integration (Vault-backed)
- **Goal:** mandatory tiered verification (ID + liveness, background check US/UK, address, credentials).
- **Build:** `api/marketplace/verification/` behind a `VerificationProvider` interface (Stripe
  Identity / Persona / Onfido — vendor TBD §A19 #4); webhook ingestion of verification results;
  `VerificationRecord` status updates; address verification feeds travel-radius; re-verification
  cadence + trigger hook. All artefacts → Vault refs only.
- **Depends on:** F3, A1; **vendor account (WS-X)**
- **Done when:** a sandbox verification flips `verificationStatus` to VERIFIED; no raw doc/report is
  stored in app tables or returned to clients; access to vault refs is logged.

### A3 — Service catalogue, modes, travel, samagri & pricing — **∥**
- **Goal:** pandit declares exactly what they do and how they reach the patron, with prices.
- **Build:** `PanditService` CRUD; mode(s) (in-person/live-remote), duration, included/patron-arranged,
  languages, **base price**; `TravelPolicy` (willTravel, maxRadiusMiles ≤100, feeModel
  flat/per-mile/banded, requiresPickup); samagri option (none / fixed / billed-at-cost). Validation:
  radius cap, currency, festival/muhurat linkage to ServiceType.
- **Depends on:** F5, A1
- **Done when:** a pandit can publish ≥1 service with a travel policy and samagri option; invalid
  radius (>100) is rejected.

### A4 — Availability & scheduling — **∥**
- **Goal:** working hours, blackout, lead time, buffer, accept-mode; no double-booking.
- **Build:** `api/marketplace/availability/` — recurrence rules, blackout dates, per-service min
  lead time, travel buffer between in-person bookings, capacity (one ceremony/slot), auto vs manual
  accept-mode + response window. Availability lookup feeds search + booking. Optional Google/Apple
  calendar two-way sync reuses §5.14 export plumbing **[P2]**.
- **Depends on:** F2 (overlap constraint), A1
- **Done when:** a booked slot is unavailable to others; lead-time/blackout rejects out-of-policy
  requests; manual-accept bookings expire after the response window.

### A5 — Provider dashboard
- **Goal:** the pandit's operational home.
- **Build:** read APIs for upcoming/past bookings + status, accept/decline pending, reschedule/cancel
  within policy; earnings (pending-in-escrow / available / paid-out) + payout history + downloadable
  statements (§A15.5); reviews received; response-rate/completion-rate/rating trends; standing
  indicator; messaging inbox link.
- **Depends on:** A1, A3, A4, C1, C2, D1, D3 (integrate progressively)
- **Done when:** dashboard reflects real booking/earning/review state from the respective modules.

---

## WS-B · Patron (Customer) side — **∥ with WS-A after F**

### B1 — Discovery & search
- **Goal:** find a trustworthy pandit fast (the brief's "find a pandit").
- **Build:** `api/marketplace/search/` — filters (service/ceremony, festival, mode, date+time with
  muhurat awareness, location & distance, language, tradition, price range, rating, verification
  badges); sorts (recommended default, rating, price, distance, soonest availability); result card
  payload. Geo/distance util (great-circle or PostGIS). Redis cache; target ≤1s. Ranking logic is
  stubbed here and finalised in D3 (§A8.4).
- **Depends on:** F2, F5; reads A2/A3/A4 data (build against contract, integrate as they land)
- **Done when:** filtered+sorted search returns only APPROVED+VERIFIED pandits in ≤1s typical;
  distance filter honours travel radius.

### B2 — Pandit profile view — **∥**
- **Goal:** the public profile a patron evaluates.
- **Build:** read API assembling bio, services+prices, modes/travel terms, languages, tradition,
  verification badges, availability preview, moderated gallery, reviews, aggregates. Actions surface:
  check availability, message (pre-booking), book, favourite, share. **Open to Basic/guests.**
- **Depends on:** F2, A3
- **Done when:** profile renders for an anonymous user; PII (exact address etc.) is absent.

### B3 — Booking flow + Quote contract (the pivot point for WS-C)
- **Goal:** muhurat-aware booking with a server-authoritative itemised quote.
- **Build:** `api/marketplace/bookings/` create flow: select service+mode → pick date/time (Planner/
  Muhurat §5.6 suggests auspicious slots, cross-checked vs availability) → in-person address
  capture + **radius validation + travel-fee compute** → samagri choice → notes/sankalp/gotra →
  review quote → pay. **60-day advance window** + per-service lead-time bounds (configurable).
  Define and freeze the **Quote schema** (§A4.5: service, travel, samagri, platform fee, tax, total)
  in `api/marketplace/pricing/` — this is the contract WS-C builds against. **Client never sets price.**
- **Depends on:** F2, B2, A3, A4; Planner/Muhurat service
- **Done when:** a quote is computed server-side end-to-end; address outside radius is rejected;
  booking is created in `REQUESTED` with a frozen `priceBreakdown` + `policySnapshot`.

### B4 — Manage, reschedule, cancel, rebook, recurring
- **Goal:** patron post-booking control.
- **Build:** view upcoming/past + receipts/invoices + message thread; reschedule (subject to
  availability + lead time); cancel (drives C4 policy engine); rebook/favourite; recurring bookings
  for repeating family pujas (deep-link from Family calendar §5.8). Recurring/gift **[P2]**.
- **Depends on:** B3, C1, C4
- **Done when:** reschedule/cancel transitions fire the correct lifecycle + refund path.

---

## WS-C · Money & Lifecycle — starts after F2 + B3 quote contract

> C1 and C2 can be built **in parallel** by two agents against the Booking/Quote contracts.

### C1 — Booking lifecycle state machine + audit
- **Goal:** the explicit, auditable state machine (Architecture §4 / §A5).
- **Build:** `api/marketplace/bookings/lifecycle.py` — allowed transitions, guards, and a
  `BookingEvent` written in the **same DB transaction** as each transition. Auto-decline on response-
  window expiry (releases authorisation). In-progress/completed signals (in-person "arrived"/"started";
  remote via VideoSession log).
- **Depends on:** F2, B3
- **Done when:** illegal transitions are rejected; every transition appends a timestamped
  BookingEvent; auto-decline releases the auth.

### C2 — Stripe Connect: escrow, payouts, webhooks — **∥ with C1**
- **Goal:** authorise→capture→hold→release with idempotency and webhook-driven state.
- **Build:** `api/marketplace/payments/` — Connect onboarding for pandits (payout account); authorise
  at booking, capture to escrow on confirm, release (minus commission) after completion + holdback;
  refunds; **idempotency keys (Redis)**; **verified webhooks** as the source of truth; SCA/3-DS;
  least-privilege keys; reconciliation into the §12 ledger pattern (distinct ledger). Apple Pay /
  Google Pay at launch.
- **Depends on:** F2, B3; **Stripe Connect account (WS-X)**
- **Done when:** a sandbox booking authorises→captures→releases via webhooks; double-submit is
  idempotent; no raw card data touches platform servers.

### C3 — Commission & fee engine
- **Goal:** the revenue model itself, config-driven.
- **Build:** take-rate by service category and/or pandit tier (default flat % on service fee only;
  travel/samagri pass-through — §A19 #1); Gold perk hook (reduced fee — §A19 #7). Plugs into the
  quote (B3) and the release calc (C2).
- **Depends on:** B3, C2
- **Done when:** quote + payout reflect the configured rate; changing the config does not alter
  existing bookings (snapshot).

### C4 — Cancellation / refund / no-show policy engine
- **Goal:** the 30-day reference policy + configurable inner tiers, snapshotted per booking.
- **Build:** `api/marketplace/policy/` — outer 30-day full-refund boundary; inner tiers (default 50%
  inside 30d, 0% inside 48h/day-of — §A19 #2); pandit-cancel = full refund + standing penalty;
  no-show rules with evidence (check-in / session log). Policy **snapshot** stored on the booking;
  shown at booking + on receipt.
- **Depends on:** B3, C1, C2
- **Done when:** each cancel path computes the correct refund from the booking's *snapshot*, not
  current config; pandit-cancel dings standing (D4).

### C5 — Tax & multi-currency
- **Goal:** correct facilitator tax/VAT and currency display at quote time.
- **Build:** `api/marketplace/finance/` — per-jurisdiction tax config (US state sales tax, UK/EU VAT);
  tax line in the quote; multi-currency **display** + settlement (USD/GBP/EUR/AED) with FX; provider
  tax reporting (1099-K via Stripe) + annual statements. Multi-currency display is MVP; full
  settlement/FX can phase.
- **Depends on:** B3, C2
- **Done when:** quote shows correct tax for the patron jurisdiction; statements are downloadable.

---

## WS-D · Communication & Trust — **∥ with A/B/C**

### D1 — In-app messaging (PII-masked)
- **Goal:** per-booking + pre-booking chat without off-platform leakage.
- **Build:** `api/marketplace/messaging/` — Conversation/Message, text + image attachments
  (object storage); **contact-info masking + off-platform-circumvention detection** (no phone/email/
  payment links); pre-booking Q&A (rate-limited); retention for dispute evidence; reportable.
- **Depends on:** F2; B2 (pre-booking), B3 (per-booking)
- **Done when:** a message containing a phone number/email is masked/flagged; pre-booking is
  rate-limited and exposes no private contact.

### D2 — Notifications (extends v2.0 §11)
- **Goal:** transactional email (mandatory at launch) + push/in-app across the trigger matrix.
- **Build:** email templates + push triggers for: requested/confirmed, accept/decline deadline,
  receipt/invoice, reminders (T−48h / T−2h, remote join link near start), reschedule/cancel,
  new message, completion + review request, payout/statement, dispute opened/resolved. Respect
  quiet hours, language and channel prefs (§11.2). Reuse existing reminder fan-out.
- **Depends on:** F4; integrates with C1/C2/D1/D3 events
- **Done when:** each lifecycle event emits the right channels; quiet hours honoured; email retried/
  bounce-handled.

### D3 — Reviews, ratings & ranking
- **Goal:** two-way verified reviews + the explainable "recommended" ranking.
- **Build:** `api/marketplace/reviews/` — review allowed only on a completed+paid booking; **two-way
  double-blind reveal** (reveal after both submit or window closes); aggregates (avg, count,
  recency-weighted) + response/completion rate; moderation via §9.4 flag-and-review. Finalise the
  **ranking** (§A8.4): blend rating, count, recency, completion, response time, proximity/
  availability, price competitiveness; new-pandit visibility boost; anti-gaming; **explainable** +
  ops-tunable. Feeds B1 default sort.
- **Depends on:** C1 (completion), B1 (search sort)
- **Done when:** only verified bookings can review; reveal is double-blind; ranking weights are
  config-driven and explainable.

### D4 — Trust, safety & disputes
- **Goal:** the safety machinery a home-visit marketplace requires.
- **Build:** `api/marketplace/safety/` — **address privacy** (reveal exact address to pandit only
  after confirmed+paid in-person booking; hide after completion); in-person SOS/support affordance;
  misconduct reporting; **dispute workflow** (open → evidence: messages/session logs/photos → ops
  decision → refund/release/partial; **payout frozen** meanwhile); fraud/abuse detection (duplicate
  account, fake review, collusion, off-platform leakage, velocity limits); **provider standing
  score** (completion/cancellation/response/rating/complaints → ranking + warnings/suspension).
- **Depends on:** C1, C2, D1, D3
- **Done when:** address is gated by booking state; opening a dispute freezes the payout; standing
  recomputes on the input signals.

### D5 — Live 1:1 video **[P2 fast-follow]**
- **Goal:** real-time remote ceremony delivery.
- **Build:** `api/marketplace/video/` behind a `VideoProvider` interface (Agora/Twilio/LiveKit —
  §A19 #6); waiting room, scheduled join window tied to booking, network-adaptive + audio-only
  fallback, join/leave session log (feeds completion/no-show), optional both-party-consented
  recording → access-controlled object storage.
- **Depends on:** C1, B3; **video vendor (WS-X)**
- **Done when:** a 1:1 session joins within the window; the session log drives completion; recording
  is off by default and requires both-party consent.

---

## WS-E · Admin & Operations — **∥ with A/B/C/D**

Each reuses the existing admin pattern (`api/routers/admin/`, `api/admin/rbac.py`, `api/admin/audit.py`)
and lands in `apps/admin`. RBAC + full audit trail on every action.

- **E1 — Provider approval queue** — review verification, approve/reject with reasons, request changes. *(Depends: A1, A2)* **∥**
- **E2 — Service-taxonomy management** — curate ServiceTypes/festivals/ceremonies + §5.5/§5.6 links. *(Depends: F5)* **∥**
- **E3 — Commission & fee configuration** — take-rate by category/tier, travel/samagri policy, cancellation-tier config. *(Depends: C3, C4)* **∥**
- **E4 — Booking & dispute console** — search bookings, intervene, issue refunds, resolve disputes, manage no-shows. *(Depends: C1, C4, D4)* **∥**
- **E5 — Payout management & reconciliation** — balances, holds, failures, finance exports. *(Depends: C2, C5)* **∥**
- **E6 — Content moderation + fraud dashboards** — profiles/galleries/reviews/messages queues; fraud manual-review queues. *(Depends: D1, D3, D4)* **∥**

---

## WS-G · Clients — web leads, mobile **∥** once a flow's API contract is frozen

Use `packages/api-client-ts` as the contract source of truth; design via the Aqualeo design system
(`packages/design-tokens`). Build each flow web-first, then iOS/Android in parallel.

### Web (`apps/web`, Next.js + Tailwind) — SSR for SEO on browse surfaces
- **G-W1** Provider onboarding + verification + catalogue + availability screens. *(A1–A4)*
- **G-W2** Discovery/search + filters/sort + pandit profile (public, SSR). *(B1, B2)*
- **G-W3** Booking flow + itemised quote + payment (Stripe Elements / Payment Element). *(B3, C2, C5)*
- **G-W4** Patron manage/reschedule/cancel + provider dashboard. *(B4, A5)*
- **G-W5** Messaging UI + notifications preferences; video room **[P2]**. *(D1, D2, D5)*
- **G-W6** Deep-link entry points: Muhurat finder, Festival detail, Samagri checklist, Family calendar. *(§A1.1)*

### iOS (`apps/ios`, SwiftUI) & Android (`apps/android`, Compose) — **∥ with each other and with web**
- **G-M1** Browse/search/profile (open to all). *(B1, B2)*
- **G-M2** Booking + Apple Pay / Google Pay + quote. *(B3, C2)*
- **G-M3** Provider dashboard + availability + accept/decline. *(A4, A5)*
- **G-M4** Messaging + push notifications; video **[P2]**. *(D1, D2, D5)*
- **G-M5** Deep-link entry points + upgrade prompt at checkout for Basic users. *(§A4.1, §A14)*

### Admin (`apps/admin`, React) — WS-E screens.

---

## WS-X · Continuous / launch-gating (runs alongside everything)

- **X1 — Vendor setup:** Stripe Connect account + Stripe Identity (or Persona/Onfido); background-check
  provider (US/UK); video SDK trial (Agora/Twilio/LiveKit). *Gates A2, C2, D5.*
- **X2 — Legal & policy artefacts (§A15.4):** Pandit Partner Agreement, patron booking terms,
  cancellation/refund policy, code of conduct, liability/indemnity, dispute terms — versioned +
  acceptance-logged. *Gates A1 acceptance + launch.*
- **X3 — App Store / Play compliance review (§A15.3):** confirm external-payment carve-out wording for
  in-person + live-remote at submission; keep subscriptions on IAP. *Gates store submission.*
- **X4 — Tax/finance config per region (§A15.5):** facilitator tax/VAT config + finance sign-off
  before each launch region. *Gates regional launch.*
- **X5 — NFR & observability:** booking/payout tracing, alerts (failed payments, stuck payouts,
  dispute spikes, video join failures), ≤1s search SLO, 99.9% read posture. Reuse `infra/observability`.
- **X6 — Accuracy / licensing gate (unchanged):** Swiss Ephemeris commercial licence secured before
  any public/paid build. *Hard launch gate.*

---

## Suggested execution order (with parallel agents)

1. **Sprint 0 — Foundation (serial):** F1 → F2 → F3 → F4 → F5. Start X1 + X2 in parallel.
2. **Sprint 1 — Two lanes in parallel:**
   - Agent A: **A1 → A2 → A3 ∥ A4** (provider side).
   - Agent B: **B1 ∥ B2 → B3** (patron side; freeze the Quote contract in B3).
3. **Sprint 2 — Money + comms, parallel:**
   - Agent C1: **C1** (lifecycle) ∥ Agent C2: **C2** (Stripe) → then **C3, C4, C5**.
   - Agent D: **D1, D2, D3, D4** as their deps land.
4. **Sprint 3 — Surfaces, parallel:** **WS-E** (admin) ∥ **WS-G web** ∥ **WS-G mobile**; **A5/B4** wire-up.
5. **Sprint 4 — Hardening + launch gates:** X3, X4, X5, X6; end-to-end booking→payout→review→dispute
   tests; security/privacy review (address privacy, vault, PII masking).
6. **Phase 2:** **D5 live video** + calendar sync + advanced ranking + standing automation + group/
   recurring/gift bookings + promos + booking protection.
7. **Phase 3:** India + UAE supply (UPI, GST/TDS, local KYC, AED/INR) + samagri-kit partners +
   tipping + concierge + temple/pilgrimage tie-ins.

---

## MVP definition of done (Addendum A §A18.1)

Provider onboarding + verification · service catalogue (festivals/pujas) with travel & samagri ·
patron search/filter/sort · booking with muhurat-aware scheduling (60-day window) · Stripe escrow +
commission + payout · cancellation/refund policy (30-day reference) · transactional email + push ·
in-app messaging · two-way reviews · admin approval/dispute/payout consoles · single launch region
(US/UK), multi-currency display. **In-person first; live-remote video fast-follows (D5).**

---

*End of Development Plan — Pandit Services Marketplace. Pairs with `docs/architecture-marketplace.md`.*
