# The Pandit — Architecture (Marketplace Extension)

**Document:** Architecture v1.2 — "Book a Pandit" Pandit Services Marketplace
**Extends:** Architecture v1.1 (`The-Pandit-Architecture.docx`)
**Implements:** Requirements Addendum A — Pandit Services Marketplace
**Reads with:** Requirement Specifications v2.0 · Development Plan v1.1 · `docs/dev-plan-marketplace.md`
**Status:** Draft for build — feeds Claude Code as architectural context
**Date:** June 2026

> This file is the canonical architectural context for the marketplace build. It does **not**
> replace Architecture v1.1 — it adds to it. Where it touches an existing layer or entity, the
> cross-reference to v1.1 / Addendum A is given. Anything not mentioned here is unchanged from v1.1.

---

## 0 · How the marketplace fits the existing system

The Pandit today is a modular service-oriented backend behind a **single versioned REST/JSON API
gateway** (`services/api`, FastAPI), consumed by three thin clients (`apps/ios`, `apps/android`,
`apps/web`) plus a React admin console (`apps/admin`). The Panchang Computation Service
(`services/panchang`) is the only writer of raw astronomical truth; everything else reads its
cached output. Festival rules live in `services/festivals`. Entitlement is enforced **at the
gateway** via `require_tier(...)` (`services/api/src/api/dependencies.py`), not in client code.

The marketplace is a **new domain inside the same gateway**, not a separate public surface. It
reuses auth, the tier gate, the CMS/admin patterns, notifications and the Sensitive Vault concept,
and it deep-links from existing surfaces (Muhurat finder §5.6, Festival detail §5.5.3, Samagri
checklist §7.3, Family calendar §5.8).

### Architectural north star (unchanged + 4 marketplace additions)

The four existing north-star rules (engine is the single source of astronomical truth; Panchang is
precomputed/cached; religious content is CMS data; clients are thin) still hold. The marketplace
adds four more:

5. **Money is never client-trusted.** Price, commission, tax and entitlement are computed
   server-side at the gateway; the client never sets an amount. Booking state is driven by Stripe
   **webhooks**, never by client callbacks.
6. **No double-booking, ever.** Slot reservation and payment authorisation are atomic. A confirmed
   booking holds the slot under a DB constraint, not application luck.
7. **Verification is a hard gate.** A pandit is invisible until KYC passes *and* ops approves.
   Sensitive verification artefacts live only in the Vault, never in client responses.
8. **Two ledgers, reconciled, never co-mingled.** Subscriptions stay on Apple IAP / Google Play
   Billing / Stripe-web (§6). Marketplace bookings are per-transaction via **Stripe Connect**.
   A bookable physical/person-to-person service is never packaged as an IAP SKU (§A15.3).

---

## 1 · New domain services (extends v1.1 §03 "Components")

v1.1 defines ten domain services (Panchang, Calendar, Festival, Reminders, Planner/Muhurat, PDF,
AI Assistant, CMS, Users, Subscriptions). The marketplace adds the following, implemented as
**modules inside `services/api`** for the MVP (single deployment, clean module boundaries — same
posture as the existing modules), extractable to independent services later.

| # | Service / module | Responsibility | Lives in |
|---|---|---|---|
| 11 | **Provider (Pandit) Profile & Catalogue** | Pandit accounts, public profile, service catalogue (PanditService → ServiceType taxonomy), travel/samagri/pricing config. | `api/marketplace/providers/` |
| 12 | **Verification & Trust (KYC)** | Government-ID + selfie liveness, background check (US/UK), address verification, credential attestation, re-verification cadence. Writes refs to the Vault. | `api/marketplace/verification/` |
| 13 | **Availability & Scheduling** | Working hours, blackout dates, lead time, buffer, accept-mode; conflict prevention / no-double-booking; optional calendar sync (reuses §5.14 export). | `api/marketplace/availability/` |
| 14 | **Discovery & Search** | Filter/sort/rank pandits (service, festival, mode, date+muhurat, location/distance, language, tradition, price, rating, badges); explainable "recommended" ranking (§A8.4). | `api/marketplace/search/` |
| 15 | **Booking & Lifecycle** | Booking creation, the explicit state machine (§A5), BookingEvent audit, reschedule/cancel, recurring/rebook. | `api/marketplace/bookings/` |
| 16 | **Quote & Pricing Engine** | Server-side itemised quote: base + travel + samagri + platform fee + tax. Authoritative; client never computes. | `api/marketplace/pricing/` |
| 17 | **Payments, Escrow & Payouts** | Stripe Connect escrow (authorise→capture→hold→release), commission take-rate, payouts, refunds, webhooks, idempotency, reconciliation into the §12 ledger pattern. | `api/marketplace/payments/` |
| 18 | **Cancellation/Refund Policy Engine** | 30-day reference policy + configurable inner tiers; policy **snapshot** stored on each booking; no-show rules. | `api/marketplace/policy/` |
| 19 | **Messaging** | Per-booking + pre-booking chat (text/images); PII masking + off-platform leakage detection; retention for disputes. | `api/marketplace/messaging/` |
| 20 | **Reviews & Ranking** | Two-way verified-booking reviews with double-blind reveal; aggregates; moderation (reuses §9.4 flag-and-review). | `api/marketplace/reviews/` |
| 21 | **Live Video (1:1)** | Real-time remote ceremony via embedded SDK (waiting room, scheduled join window, session log, optional consented recording). Phase-2 fast-follow. | `api/marketplace/video/` |
| 22 | **Trust, Safety & Disputes** | Address privacy, SOS/support during home visits, dispute workflow (open→evidence→ops decision→refund/release), fraud/abuse detection, provider standing score. | `api/marketplace/safety/` |
| 23 | **Tax & Finance** | Marketplace-facilitator sales tax (US), VAT (UK/EU), platform-fee vs earnings treatment, multi-currency display/settlement, provider tax reporting (1099-K via Stripe). | `api/marketplace/finance/` |

Existing services that the marketplace **reads from / extends**: Users & Profiles (dual role),
Subscriptions (the Silver gate), Planner/Muhurat (auspicious-slot suggestion in booking),
Festival rules (officiation taxonomy), Notifications (§11 transactional channels), CMS/Admin
(taxonomy + moderation + approval queue), Sensitive Vault (§15.1).

---

## 2 · Persistence — the spine the marketplace requires

> **Decision (confirmed):** introduce a real relational layer. The current API modules use
> in-process dict stores; that is acceptable for read-mostly Panchang/CMS data but **not** for
> bookings, escrow and payouts, which demand transactional integrity, atomic slot reservation and
> auditability. `services/api/src/api/settings.py` already names
> `postgresql+asyncpg://…` — this wires it up for real.

**Stack:** PostgreSQL (per v1.1 §5.5) + **SQLAlchemy 2.x async** + **Alembic** migrations, with a
thin **repository pattern** per module. Redis (already a dependency) backs the search/availability
cache, idempotency keys and rate limits. The existing in-memory CMS/admin stores are left as-is for
now; new marketplace tables are additive.

**Integrity rules baked into the schema:**

- **No double-booking:** a partial unique index / exclusion constraint on
  `(pandit_id, time-range)` for active booking states prevents overlapping confirmed slots at the
  DB level — application code cannot bypass it.
- **Money is append-only & auditable:** `Payment`, `Payout`, `Refund` and `BookingEvent` are
  written transactionally with the booking state transition; never updated in place destructively.
- **Policy immutability:** the cancellation/refund + fee terms in force at booking time are
  serialized into `Booking.policySnapshot` so later config changes never rewrite an existing
  booking's terms (§A7.1).

---

## 3 · Data model additions (extends v1.1 §04 / Addendum A §A13)

New core entities. **Sensitive fields** (ID images, background-check references, exact ceremony
addresses) live in the **encrypted Sensitive Vault** (v1.1 §5.1 / §15.1) — access-logged, excluded
from analytics, minimised in API responses. The tables below store only **references** to vault
records, never the raw sensitive data.

| Entity | Key fields | Notes |
|---|---|---|
| **Pandit** | id, userId, displayName, bio, baseLocationId, languages, tradition, experience, verificationStatus, ratingAgg, standingScore, payoutAccountRef | Verification docs → Vault |
| **PanditService** | id, panditId, serviceTypeId, modes[], durationMin, basePrice, currency, samagriOption, samagriPrice, travelPolicy | One per offered service |
| **ServiceType** | id, category, name, festivalRef?, muhuratEventRef?, taxonomyTags | Admin-curated; links §5.5 / §5.6 ids |
| **TravelPolicy** | panditId, willTravel, maxRadiusMiles (≤100), feeModel, requiresPickup | Drives distance/fee |
| **Availability** | panditId, rules, blackoutDates, leadTimeMin, acceptMode, bufferMin | Prevents double-booking |
| **Booking** | id, patronUserId, panditId, panditServiceId, mode, startTime, tz, addressRef?, samagriChosen, status, priceBreakdown, policySnapshot, muhuratRef? | Core record |
| **BookingEvent** | bookingId, fromState, toState, actor, timestamp, reason | Lifecycle audit (§A5) |
| **Payment** | id, bookingId, stripeRefs, amount, currency, commission, taxes, status | Escrow + capture |
| **Payout** | id, panditId, amount, period, status, statementRef | Stripe Connect |
| **Refund** | id, bookingId, amount, reason, policyTier | Cancellation / dispute |
| **Review** | id, bookingId, authorRole, stars, body, moderationState, publishedAt | Two-way, verified, double-blind |
| **Conversation / Message** | id, bookingId?, participants, body/attachmentRef, flags | Masked PII |
| **VideoSession** | bookingId, provider, joinWindow, joinLog, recordingRef? | Live remote |
| **Dispute** | id, bookingId, raisedBy, reason, evidenceRefs, state, resolution | Freezes payout |
| **VerificationRecord** | panditId, idStatus, bgCheckStatus, addressStatus, lastVerifiedAt | Refs in Vault |

### 3.1 Key relationships

- A **User** may hold a **Patron** role and/or a **Pandit** role (single login, dual role).
- A **Pandit** has many **PanditServices**, one **Availability**, one payout account, many
  **Bookings** and **Reviews**, one **VerificationRecord**, one **standingScore**.
- A **Booking** belongs to one Patron and one Pandit, references one PanditService, has one
  **Payment**, many **BookingEvents**, optionally one **VideoSession**, up to two **Reviews**, one
  **Conversation**, and may reference a **Muhurat / FestivalOccurrence** from v2.0.

---

## 4 · The booking lifecycle (state machine — §A5)

Every transition is timestamped and written as a `BookingEvent` in the same DB transaction as the
state change and any money movement.

```
                 ┌────────────┐   pandit accepts / auto    ┌───────────┐
   patron pays → │ REQUESTED  │ ─────────────────────────► │ CONFIRMED │
   (authorised) └─────┬──────┘                             └─────┬─────┘
                       │ no accept in response window             │ capture → escrow
                       ▼ (auto-decline, auth released)            │
                 CANCELLED_PANDIT                                 ▼
                                                          ┌────────────────┐
                            reschedule proposed ◄────────►│ RESCHEDULE_PEND │
                                                          └────────┬───────┘
                                                                   ▼
                                            ┌──────────────┐   start signal   ┌─────────────┐
                                            │  CONFIRMED   │ ───────────────► │ IN_PROGRESS │
                                            └──────────────┘                  └──────┬──────┘
                                                                                      ▼
   ┌────────────┐  ┌────────────────┐  ┌─────────────────┐  ┌──────────┐   completion confirmed
   │  DISPUTED  │◄─│   COMPLETED    │  │ CANCELLED_PATRON │  │ NO_SHOW  │ ◄───────────┘
   └─────┬──────┘  └───────┬────────┘  └────────┬────────┘  └────┬─────┘
         │ ops resolves    │ holdback elapsed   │ refund/policy   │ no-show rules
         ▼                 ▼ release to pandit   ▼                 ▼
   REFUNDED / CLOSED   (payout − commission)   REFUNDED        resolved
```

| State | Money |
|---|---|
| Requested | Authorised (held) |
| Confirmed | Captured into escrow |
| Reschedule pending / In progress | Held |
| Completed | Payout scheduled (total − commission − fees) after holdback |
| Cancelled — patron | Refund per policy (§A7) |
| Cancelled — pandit | Full refund + pandit penalty/standing impact |
| No-show | Resolved per §A7.3 (evidence: check-in / session log) |
| Disputed | **Payout frozen** pending resolution |
| Refunded / Closed | Terminal |

---

## 5 · Money flow & external integrations (extends v1.1 §5.5)

### 5.1 Payments — Stripe Connect (escrow)

- **Connected accounts:** Stripe Connect (Express/Custom) per pandit; KYC-for-payout handled by
  Stripe; platform is the escrow holder.
- **Capture model:** authorise at booking → capture to platform/escrow on confirmation → release
  pandit share after `COMPLETED` + a short **holdback** (default 24–72h dispute buffer).
- **Commission:** configurable take-rate by service category and/or pandit tier, deducted before
  payout. Travel + samagri pass through to the pandit (commission policy on these is a config flag).
- **Hard rules:** idempotent operations (idempotency keys in Redis), **webhook-verified** state
  transitions, SCA/3-DS where required, least-privilege keys, no raw card data on platform servers
  (PCI handled by Stripe). Receipts reconcile into the existing Subscription/payment ledger pattern
  (§12) but stay a **distinct ledger**.

### 5.2 Verification / KYC

Pluggable provider behind a `VerificationProvider` interface (Stripe Identity / Onfido / Persona —
vendor is an open decision). Document + selfie liveness; background check where legally available
(US/UK); address verification feeding the travel-radius calc. **Raw reports are never stored in the
app** — only status + a vault reference.

### 5.3 Live video (Phase 2)

Embedded 1:1 SDK behind a `VideoProvider` interface (Agora / Twilio Video / LiveKit — open
decision). Waiting room, scheduled join window tied to the booking, network-adaptive with
audio-only fallback, join/leave session log feeding completion/no-show resolution, optional
both-party-consented recording → access-controlled object storage.

### 5.4 Tax & multi-currency

Marketplace-facilitator tax engine (per-jurisdiction config): US state sales tax, UK/EU VAT.
Tax shown to the patron **at quote time**. Multi-currency display + settlement (USD/GBP/EUR/AED),
FX handling on cross-border bookings. Provider tax reporting via Stripe (1099-K) + downloadable
annual statements.

### 5.5 Suggested technology additions

| Concern | Choice | Rationale |
|---|---|---|
| Marketplace payments | **Stripe Connect** (Express) | Escrow, split payments, payout KYC, 1099-K |
| Identity verification | Stripe Identity / Persona / Onfido | Doc + liveness; vendor TBD (§A19) |
| Background check | Market-legal provider (US/UK) | Status only; report never stored |
| Live 1:1 video | LiveKit / Agora / Twilio Video | Real-time; vendor TBD on cost/region |
| Search | Postgres + Redis (MVP); Meilisearch/OpenSearch (scale) | ≤1s results; geo + facet filters |
| Distance / geo | PostGIS or great-circle util | Travel radius + fee bands |
| Persistence | PostgreSQL + SQLAlchemy async + Alembic | Transactional integrity for money/slots |
| Idempotency / cache | Redis (already present) | Idempotency keys, search/availability cache |
| Email (transactional) | Existing §11 channel + templates | Mandatory at launch (the brief) |

---

## 6 · Entitlement, App Store & compliance (extends v1.1 §5.1, Addendum A §A14–A15)

- **Gate:** booking **checkout** requires an active **Silver or Gold** subscription, enforced at
  the gateway via the existing `require_tier(SubscriptionTier.SILVER)` dependency — Gold inherits.
  **Browsing pandit profiles/prices is open** to Basic/guests (SEO + conversion); the upgrade
  prompt appears only at checkout.
- **Two ledgers:** subscription unlocks the *ability* to book; each booking is charged
  per-transaction via Stripe. Keep distinct, reconcile.
- **App Store / Play:** in-person services are physical real-world services; live 1:1 video is a
  real-time person-to-person service — both eligible for external (Stripe/Apple Pay/Google Pay)
  payment **outside IAP** (Apple Guideline 3.1.3(d)/3.1.5; Google real-world-service carve-out).
  Subscriptions stay on IAP/Play Billing. Confirm wording with Apple/Google at submission.
- **Sensitive data:** pandit ID docs, background-check refs, patrons' exact addresses → Vault,
  access-logged, excluded from analytics, minimised in responses. **Address privacy:** the exact
  ceremony address is revealed to the pandit only after a confirmed, paid in-person booking, and
  hidden again after completion.

---

## 7 · Cross-cutting concerns (extends v1.1 §05)

- **Booking integrity:** payment authorisation + slot reservation are atomic; DB-level overlap
  constraint; webhook-driven state.
- **Observability:** trace every booking and payout end-to-end; alert on failed payments, stuck
  payouts, dispute spikes, video join failures, cache-miss spikes (reuse `infra/observability`).
- **Performance:** pandit search/results ≤1s typical; availability checks near-real-time; booking
  and payment paths on the same 99.9% read-SLO posture as v2.0.
- **Privacy / GDPR:** right-to-export / right-to-delete extends to bookings and messages.
- **Audit & RBAC:** every ops action role-based + audited (reuse v2.0 §15.2 / existing
  `api/admin/rbac.py` + `api/admin/audit.py`).
- **Accuracy gate unchanged:** the Swiss Ephemeris commercial licence remains a hard launch gate
  before any public/paid build (v1.1 licensing).

---

## 8 · Admin & operations (extends v1.1, Addendum A §A12)

The React admin console (`apps/admin`) gains: **provider approval queue** (review verification,
approve/reject with reasons, request changes), **service-taxonomy management**, **commission/fee
config**, **booking & dispute console**, **payout management & reconciliation exports**, **content
moderation** (profiles/galleries/reviews/messages), and **fraud dashboards + manual-review queues**.
All reuse the existing admin router pattern (`api/routers/admin/`), `rbac.py` and `audit.py`.

---

## 9 · Phasing (extends v1.1 §06; mirrors Addendum A §A18)

| Phase | Marketplace scope |
|---|---|
| **MVP** | Provider onboarding + verification; service catalogue (festivals/pujas) with travel & samagri; patron search/filter/sort; booking with muhurat-aware scheduling (60-day window); Stripe escrow + commission + payout; cancellation/refund policy (30-day reference); transactional email + push; in-app messaging; two-way reviews; admin approval/dispute/payout consoles; single launch region (US/UK), multi-currency **display**. **In-person first; live-remote video fast-follows.** |
| **Phase 2** | Live 1:1 video at scale + recording; advanced ranking; standing/quality automation; group/multi-pandit bookings; recurring & gift bookings; promo/referrals; richer fraud tooling; booking protection. |
| **Phase 3** | India + UAE supply (UPI, GST/TDS, local KYC, AED/INR); samagri-kit partners; tipping; concierge; pilgrimage/temple-event tie-ins (§7.6, §7.8). |

---

## 10 · Open decisions carried from Addendum A §A19 (defaults assumed for the build)

| # | Decision | Default assumed in the plan |
|---|---|---|
| 1 | Commission rate; applies to travel/samagri? | Flat % on service fee only; travel/samagri pass-through |
| 2 | Inner cancellation tiers | 50% inside 30d; 0% inside 48h / on the day |
| 3 | Payout holdback length | 24–72h dispute buffer |
| 4 | Background-check depth per market | Max permitted in US/UK; disclosed to pandit |
| 5 | Default recording of remote sessions | Off by default; opt-in, both-party consent |
| 6 | Video SDK vendor | Evaluate Agora vs Twilio vs LiveKit on cost/region |
| 7 | Gold-tier marketplace perks | Reduced platform fee + priority dispute support |
| 8 | Provider listing/onboarding fee | None at launch (commission model) |

All eight are config-driven, not hard-coded — see the pricing/policy/commission engines (§1).

---

*End of Architecture v1.2 (Marketplace Extension). Reads with Architecture v1.1, Requirements
Addendum A, and `docs/dev-plan-marketplace.md`.*
