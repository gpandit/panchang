# The Pandit — Requirements Document

**Version:** 3.0 (canonical consolidated baseline)  
**Date:** 2026-10-07  
**Status:** Proposed canonical build baseline; unresolved decisions are explicitly marked  
**Supersedes:** the duplicated requirements, architecture addenda, marketplace briefs, and conversation-derived requirement notes under `docs/Conversation/`, `docs/architecture/`, `docs/reqjuirements/`, and `docs/development plan/`.

## 1. Purpose and decision record

This document is the single product-requirements reference for The Pandit. It combines the
requirements, marketplace addenda, previous AI conversations, the executable accuracy policy,
and the repository's current constraints. It separates **MVP**, **Phase 2**, and **Phase 3** so
that the breadth of the product does not obscure the first shippable increment.

### 1.1 Decisions made during consolidation

| Topic | v3.0 decision |
|---|---|
| Backend | Keep the repository's Python 3.12/FastAPI modular monolith. Preserve service boundaries so later extraction is possible; do not introduce a parallel NestJS backend. |
| Panchang engine | Python `pyswisseph`, Drik Ganita, Lahiri default; only the Panchang Computation Service may use the ephemeris. |
| Mobile | Keep the existing native Swift/Kotlin direction for now. A mobile-stack ADR is required before materially expanding either client. |
| Cache grid | Configurable 0.1° latitude/longitude grid plus IANA timezone in the key. Tighten only if accuracy evidence requires it. |
| Accuracy contract | Executable policy is ±2 minutes for sunrise/sunset, ±5 minutes for anga boundaries, and exact names/labels. ±1 minute remains a stretch target. |
| API contract | `docs/Conversation/the-pandit-openapi-v1.yaml` is the aspirational source to reconcile; generated clients must not claim completeness until it matches the running FastAPI surface. |
| Eventing | Start with a transactional outbox and idempotent Redis/RQ workers in the current deployment. Add a managed event-bus adapter after the contracts are stable. |
| Marketplace scope | In-person Pandit services and a Shopify-backed pooja-items path are MVP marketplace targets; live video, group bookings, and advanced ranking are Phase 2. |
| AI storage | Start with a provider-neutral retrieval interface and PostgreSQL/pgvector-compatible boundary. Do not hard-code Pinecone/Weaviate. |
| Visual design | Agents implement functional composition and named design-token references only; they must not invent colours, typography, spacing, icons, or animation. |

### 1.2 Product vision

The Pandit is a global Hindu Panchang, calendar, planning, spiritual-lifestyle, and trusted
marketplace platform. It helps users understand the local sunrise-based Hindu day, plan religious
and family events, receive location-aware reminders, obtain printable calendars, and (when
eligible) book verified Pandits or buy pooja supplies.

The product's credibility depends on one invariant: all calendar, festival, reminder, muhurat,
and marketplace scheduling decisions use the same server-side Panchang truth.

## 2. Users and roles

| Persona | Need | Initial release |
|---|---|---|
| Guest/basic patron | View today's Panchang and major festivals | MVP |
| Silver/Gold patron | Save data, reminders, family plans, buy/book | MVP/S2-S4 |
| Pandit/provider | Verify identity, publish services, manage availability and bookings | Marketplace MVP |
| Seller/merchant | Manage pooja products and fulfilment through the seller portal | Marketplace MVP, subject to Shopify readiness |
| Content administrator | Publish rules, regional content, translations, and corrections | MVP |
| Marketplace operations | Approve providers/sellers, resolve disputes, reconcile money | Marketplace MVP |
| Finance administrator | Review ledger, payouts, refunds, tax and reconciliation | Commerce gate |
| Temple administrator | Manage temple calendars and bulk/community products | Phase 3 |

All users may hold multiple roles on one account. Sensitive birth, KYC, and ceremony-address
data is never stored in ordinary profile records.

## 3. Product principles and non-negotiables

1. **Engine first:** no downstream feature is considered complete until its Panchang inputs are
   from the canonical cache and the accuracy gate is green.
2. **Server authority:** clients never calculate Panchang values, prices, commissions, taxes,
   entitlements, booking state, or payout state.
3. **Rules over date tables:** festivals and religious content are CMS/rule data, with provenance,
   regional variants, and review workflow.
4. **Privacy by construction:** sensitive data is encrypted, access-logged, minimised, and
   excluded from analytics.
5. **Payment-rail separation:** subscriptions use Apple IAP/Google Play Billing/Stripe Web;
   Pandit services use Stripe Connect; goods use Shopify checkout. Rails are never mixed.
6. **Offline tolerance:** clients cache server results for reading, but never generate new
   Panchang results offline.
7. **Auditable money and state:** booking/order transitions, webhooks, refunds, and payouts are
   idempotent and append-only where financial or audit evidence is involved.

## 4. Functional requirements

### 4.1 Panchang and calendar (P0)

The service must accept date, latitude, longitude, IANA timezone, ayanamsa, and month scheme and
return a deterministic sunrise-to-sunrise `PanchangDay` containing:

- Tithi, Nakshatra, Yoga, Karana, Vara, Paksha;
- sunrise, sunset, moonrise, moonset;
- Amanta and Purnimanta month, Adhika/Kshaya labels;
- Shaka, Vikram, and Gujarati Samvat, Ritu, Ayana, Samvatsara;
- Rahu Kalam, Yamaganda, Gulika, Abhijit, Dur Muhurat, Varjyam, Amrit Kalam;
- Brahma Muhurat, Nishita, Choghadiya, Hora, and Gowri where applicable;
- interval start/end instants in UTC, local offset minutes, and `hoursFromSunrise` (including
  values greater than 24 for 24-plus display);
- flags for kshaya, vriddhi, carries-over, and sunrise fallback.

It must support Lahiri by default, an explicit override, Amanta and Purnimanta, DST, Adhika and
Kshaya Maas, Kshaya and Vriddhi Tithi, and a documented high-latitude fallback. The cache warms
at least 15 months for popular locations and computes a miss once under a per-key lock.

**Acceptance:** reference fixtures cover at least 500 days and 10 locations before S1 is declared
complete; the executable harness enforces ±2 minutes rise/set, ±5 minutes boundaries, and exact
names/labels. Every consumer uses this cache.

### 4.2 Calendar views (P0/S2)

Provide day, week, month, year, and 12–15-month views with navigation, festival/vrat markers,
notes, bookmarks, reminders, moon phase, and share/export actions. The day view loads from cache
within 2 seconds on a normal connection. The web and mobile clients cache the current month and
recently viewed days for offline reading.

### 4.3 Festivals, vrats, and CMS (P0/S1-S2)

Festival rules are versioned JSON data over tithi, nakshatra, paksha, lunar/solar month, anchor,
scheme, region, priority, and tie-break. The resolver produces `FestivalOccurrence` records for
locations and years, including Adhika/Kshaya and regional variants. Initial recurring cycles are
Ekadashi, Pradosham, Sankashti, Purnima, Amavasya, and Sankranti.

Published CMS content may include descriptions, significance, puja guidance, katha, mantras,
translations, samagri, regional variations, and source attribution. Lifecycle: Draft → In Review
→ Published → Archived. Only published content is public or eligible for AI retrieval. Users may
track vrats as planned, observed, missed, or completed with sankalp and notes.

### 4.4 Personal calendar and reminders (S2 basic; S6 lunar recurrence)

Users can create notes, bookmarks, and reminders tied to Gregorian dates, festival references,
Tithi, Nakshatra, muhurat windows, sunrise/sunset, or personal events. Reminder offsets include
at-time, 5/15/30 minutes, 1 hour, 1 day, 3 days, and 1 week.

Recurring rules resolve over a rolling 15-month horizon from the Panchang cache. Kshaya Tithi uses
the rule's regional convention; Vriddhi Tithi fires once only. A location change re-resolves all
future occurrences. Basic is limited to 5 notes, 5 bookmarks, and 5 reminders; Silver and Gold
remove those limits.

### 4.5 Muhurat and life planning (S2/S3)

The planner scans a date range for event types such as wedding, griha pravesh, namakaran,
annaprashan, mundan, purchase, business launch, travel, education, and puja. It returns
best/good/avoid classifications, scored factors, warnings, and an explanation based on the same
cached Panchang and avoidance windows. Users can save, share, export, set a reminder, or deep-link
to a Pandit search. Gold adds advanced planning and AI explanations.

### 4.6 Family features (S2/S3)

Users can create family groups, invite members, assign admin/member roles, and share calendar
events. Family birth data lives only in the Vault; derived Tithi/Nakshatra fields may be stored
for display. Use optimistic versioning for shared edits and document conflict resolution.
Silver supports up to five members; Gold is unlimited.

### 4.7 PDFs, sharing, and integrations (S2/S3)

Calendar generation is asynchronous and produces signed object-storage URLs. It supports 12–15
months, regional/language preferences, A4/A3/Letter/Legal and later branded/CMYK templates. The
platform exports PDF, PNG, iCal, and shareable links/cards. Large work is queue-driven.

### 4.8 Identity, subscriptions, and entitlements (P0)

Support guest mode, email/phone, Google/Apple OIDC, refresh-token rotation, profile/location
preferences, and GDPR/UAE export/delete. Basic, Silver, and Gold entitlements are enforced at the
gateway. Subscription receipts from Apple, Google, and Stripe Web reconcile to one server-side
subscription record. Browsing marketplace profiles/products is open; Pandit and goods checkout
requires Silver or Gold.

### 4.9 Notifications (S2)

Support APNs, FCM, in-app, and transactional email; SMS is optional. Users control categories,
quiet hours, language, timing, and sound. Delivery is idempotent, retried, and tracked.

### 4.10 Pandit services marketplace (S4; in-person first)

Providers must complete agreements, profile/service setup, identity/KYC, payout onboarding, and
operations approval before discovery. Services include mode, duration, language, tradition, base
price, samagri option, travel policy (maximum 100 miles), lead time, buffers, availability,
manual/automatic acceptance, and blackout dates.

Patrons search by service, festival, mode, date/time, location, language, tradition, price,
rating, verification, and availability. Booking validates entitlement, date window (up to 60
days), lead time, travel radius, availability, and an itemised server-side quote. Address data is
revealed only after paid confirmation and hidden after completion.

Authoritative states: `requested`, `confirmed`, `reschedule_pending`, `in_progress`, `completed`,
`cancelled_by_patron`, `cancelled_by_pandit`, `no_show`, `disputed`, `refunded`, `closed`.
Every transition writes a `BookingEvent`. The default policy snapshot is 100% refund at least 30
days before, 50% inside 30 days, and 0% inside 48 hours; policy is immutable per booking.

MVP includes Stripe Connect authorisation/capture, escrow/holdback, refunds, messaging with PII
masking, verified two-way reviews, notifications, and operations consoles. Live video, group
bookings, gifts, comparison view, and advanced ranking are Phase 2.

### 4.11 Pooja-items marketplace (S5; Shopify-backed)

Shopify remains the catalogue, inventory, tax, cart, hosted checkout, and fulfilment authority.
The platform provides seller onboarding/KYC, product/festival/samagri mapping, order mirror,
seller splits, review/return/dispute surfaces, and payout accounting. Product prices are never
authoritatively copied into platform tables. Physical goods never use IAP.

### 4.12 Ask The Pandit (S6)

The assistant uses published CMS content plus structured Panchang tools. It must cite sources,
state regional variation, refuse unsupported ritual claims, protect sensitive data, apply tier
metering, and append a qualified-pandit/family-tradition disclaimer. It must say when no grounded
answer is available; it must not invent ritual instructions. Query retention is opt-in or redacted.

## 5. Non-functional and compliance requirements

- Cached Panchang day p95 ≤2 seconds; marketplace search typically ≤1 second; API availability
  target 99.9% monthly.
- Booking slot reservation and payment intent are atomic from the application's perspective and
  protected by database constraints under concurrency.
- All external webhooks are signature-verified, idempotent, retried, dead-lettered, and reconciled.
- Sensitive data uses separate vault access control, encryption, audit logs, retention/deletion,
  and region pinning. No secrets, raw cards, KYC documents, or exact addresses in ordinary tables,
  analytics, logs, prompts, or client payloads.
- CI runs format, lint, type checks, unit/integration tests, contract tests, accuracy harness,
  security/privacy checks, and launch-readiness checks.
- Commercial Swiss Ephemeris licensing is a hard production-launch gate.
- Backups target RPO ≤1 hour and RTO ≤4 hours; Panchang cache is recomputable.

## 6. Tier matrix

| Capability | Basic | Silver | Gold |
|---|:---:|:---:|:---:|
| Daily Panchang; basic day/month | ✓ | ✓ | ✓ |
| Week/year; regional customisation | — | ✓ | ✓ |
| Notes/bookmarks/reminders | 5 each | Unlimited | Unlimited |
| Tithi recurrence, vrat tracker | — | ✓ | ✓ |
| Saved locations | 1 | 3 | Unlimited |
| Family members | — | 5 | Unlimited |
| PDF export | Limited | 12-month | 12–15 month HD |
| Muhurat | — | Basic | Advanced + AI |
| AI/life planner | — | — | ✓ |
| Pandit/goods checkout | Browse | ✓ | ✓ |
| Ads | Allowed | No | No |

## 7. Definition of done

A release is complete only when the relevant stage gate in `docs/design-development-plan-v3.0.md`
is proven by automated evidence, not a status claim: tests pass, OpenAPI and data migrations are
updated, source provenance is recorded, security/entitlement rules are tested, and no canonical
invariant is violated.
