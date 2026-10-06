# The Pandit — Refined Architecture Document

**Version:** 2.0 (Consolidated & Enhanced)
**Date:** July 2026
**Sources:** Architecture v1.1, Requirements v2.0, Addendum A & B
**Review Perspectives:** Sr Enterprise Architect, Lead Developer

---

## Executive Summary

This document consolidates and enhances the architecture for **The Pandit** — a Hindu Panchang, calendar, planning, and spiritual-lifestyle platform with two embedded marketplaces. It addresses all gaps identified during expert review and provides a production-ready architectural blueprint.

---

## Table of Contents

1. [Architectural Principles](#1-architectural-principles)
2. [System Context & High-Level Architecture](#2-system-context--high-level-architecture)
3. [Logical Architecture Layers](#3-logical-architecture-layers)
4. [Domain Services](#4-domain-services)
5. [Data Architecture](#5-data-architecture)
6. [API Architecture](#6-api-architecture)
7. [Event-Driven Architecture](#7-event-driven-architecture)
8. [Panchang Computation Engine](#8-panchang-computation-engine)
9. [Marketplace Architecture](#9-marketplace-architecture)
10. [Mobile & Web Client Architecture](#10-mobile--web-client-architecture)
11. [Security Architecture](#11-security-architecture)
12. [Scalability & Performance](#12-scalability--performance)
13. [Observability & Operations](#13-observability--operations)
14. [Deployment Architecture](#14-deployment-architecture)
15. [Technology Stack Decisions](#15-technology-stack-decisions)
16. [Architecture Decision Records](#16-architecture-decision-records)

---

## 1. Architectural Principles

### 1.1 North Star

1. **The Panchang engine is the single source of astronomical truth.** Nothing recomputes it independently.
2. **Panchang is precomputed and cached**, not calculated live on the device.
3. **Religious/festival content is data**, edited through a CMS, never hard-coded.
4. **Clients are thin**; the planning intelligence lives server-side and is shared across all platforms.
5. **Events drive state changes**; services communicate through an event bus for loose coupling.
6. **One payout engine** serves both marketplaces.
7. **Security by design**; sensitive data is isolated in an encrypted vault from day one.

### 1.2 Design Tenets

| Tenet | Implication |
|-------|-------------|
| Cache-first reads | Panchang, festivals, content served from cache/CDN; database is backup |
| Compute-once | Every Panchang value computed exactly once, then cached and shared |
| Async-by-default for heavy work | PDF generation, reminder fan-out, payout processing are queue-driven |
| API-first | All functionality exposed via versioned REST API; clients are consumers |
| Offline-tolerant | Clients cache current month + recent data; graceful degradation |
| Multi-region aware | Location, timezone, DST, regional calendar conventions are first-class |

---

## 2. System Context & High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL SYSTEMS                             │
│  Swiss Ephemeris │ Stripe/Connect │ Shopify │ APNs/FCM │ KYC │ LLM │
└────────┬────────────────┬────────────┬──────────┬────────┬─────┬───┘
         │                │            │          │        │     │
┌────────▼────────────────▼────────────▼──────────▼────────▼─────▼───┐
│                      API GATEWAY (versioned)                        │
│  Auth │ Rate Limit │ Entitlement │ Routing │ Response Shaping       │
└────────┬───────────────────────────────────────────────────────┬────┘
         │                                                       │
┌────────▼───────────────────────────────────────────────────────▼────┐
│                      DOMAIN SERVICES LAYER                          │
│                                                                     │
│  ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌───────────┐ ┌────────┐ │
│  │ Panchang │ │ Calendar  │ │ Festival │ │ Reminder  │ │Muhurat │ │
│  │ Compute  │ │ Assembly  │ │ & Vrat   │ │ Scheduler │ │Planner │ │
│  └──────────┘ └───────────┘ └──────────┘ └───────────┘ └────────┘ │
│                                                                     │
│  ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌───────────┐ ┌────────┐ │
│  │ Calendar │ │    AI     │ │ Content  │ │   User    │ │ Subs & │ │
│  │   PDF    │ │ Assistant │ │   CMS    │ │ Profile   │ │Billing │ │
│  └──────────┘ └───────────┘ └──────────┘ └───────────┘ └────────┘ │
│                                                                     │
│  ┌──────────────────────────┐ ┌────────────────────────────────┐   │
│  │   PANDIT MARKETPLACE     │ │   POOJA ITEMS MARKETPLACE      │   │
│  │ Booking│Escrow│Video│Msg │ │ ShopifySync│Orders│Fulfillment │   │
│  └──────────────────────────┘ └────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              SHARED PLATFORM SERVICES                        │   │
│  │ Payout Engine │ Notification │ Search │ Analytics │ Admin    │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────┐
│                      EVENT BUS (async)                               │
│  Booking events │ Payout triggers │ Notification fan-out             │
│  Content updates │ Cache invalidation │ Webhook processing           │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────┐
│                      DATA & PLATFORM LAYER                           │
│  PostgreSQL │ Redis │ S3 │ Job Queue │ Vector Store │ CDN            │
│  Ephemeris Files │ Sensitive Vault (encrypted)                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Consumer Clients

| Client | Technology | Role |
|--------|-----------|------|
| **Web App** | Next.js 14+ / Tailwind CSS | Primary consumer; SSR for SEO; Aqualeo design system |
| **iOS App** | Swift / SwiftUI | Native; widgets, lock-screen, push |
| **Android App** | Kotlin / Jetpack Compose | Native; widgets, push |
| **Admin Console** | React / Tailwind | Internal; content, marketplace ops, analytics |

---

## 3. Logical Architecture Layers

### Layer 1: Experience Layer
Three thin consumer clients + admin console. Clients render, cache for offline, and call the API. They **never** compute Panchang themselves.

**Web-Specific:**
- Next.js with SSR for SEO-critical pages (daily Panchang, festival pages)
- Tailwind CSS with Aqualeo design system (dark canvas, aqua accent)
- Consumer app uses devotional palette (saffron, gold, maroon, cream)
- Shopify Storefront API (GraphQL) for pooja items catalogue

**Mobile-Specific:**
- Native Swift/Kotlin for widget and lock-screen support
- Local SQLite/CoreData for offline cache
- Background fetch for notification scheduling
- Shopify mobile commerce SDK for items checkout

### Layer 2: API Gateway
Single versioned REST/JSON gateway handling:
- **Authentication** — JWT validation (OAuth/OIDC tokens)
- **Rate limiting** — per-endpoint, per-tier (see §6.4)
- **Entitlement checks** — subscription tier gates (Silver/Gold features)
- **Request routing** — to domain services
- **Response shaping** — field filtering, pagination
- **API versioning** — URL-based (/api/v1/, /api/v2/)

### Layer 3: Domain Services
Independent services with narrow interfaces (see §4).

### Layer 4: Data & Platform
Stores, caches, queues, and external integrations (see §5).

---

## 4. Domain Services

### 4.1 Panchang Computation Service

**Purpose:** Single source of astronomical truth. Wraps Swiss Ephemeris.

**Input:** `(date, latitude, longitude, timezone, ayanamsa, month_scheme)`

**Output:** All angas with precise start/end times, rise/set times, muhurat/avoidance windows, samvat fields.

**Characteristics:**
- Pure, deterministic, cacheable
- Only writer of raw Panchang values
- No direct client access — only via cache
- Python service with `pyswisseph` C-extension binding

**Internal Architecture:**
```
┌─────────────────────────────────────────────┐
│         Panchang Computation Service         │
│                                              │
│  ┌──────────────┐   ┌───────────────────┐   │
│  │ Swiss Ephem  │   │  Anga Calculator  │   │
│  │ (pyswisseph) │──▶│  Tithi/Nakshatra  │   │
│  │  C-extension │   │  Yoga/Karana/Vara │   │
│  └──────────────┘   └────────┬──────────┘   │
│                              │               │
│  ┌──────────────┐   ┌───────▼───────────┐   │
│  │  Rise/Set    │   │ Muhurat/Avoidance │   │
│  │  Calculator  │   │ Window Calculator │   │
│  └──────────────┘   └───────────────────┘   │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │     Edge Case Handler               │    │
│  │ Adhika/Kshaya maas │ DST │ High-lat │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │     Cache Writer                     │    │
│  │  Compute → Validate → Store → Return │    │
│  └──────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

### 4.2 Calendar Assembly Service

**Purpose:** Composes day/week/month/year/12-15 month views.

**Reads:** Panchang cache + festival occurrences + user overlays (notes, bookmarks, reminders).

**Returns:** View-ready payloads so clients stay thin.

### 4.3 Festival & Vrat Rules Service

**Purpose:** Rule engine for festival date resolution.

**Design:** Each festival is a rule (not a date). The resolver generates concrete occurrences per year/location by reading Panchang cache.

**Handles:** Ekadashi, Pradosham, Sankashti, Purnima, Amavasya, Sankranti cycles; Amanta/Purnimanta month-shift; regional variants.

### 4.4 Reminder & Scheduling Service

**Purpose:** Resolves recurrences into concrete fire-times; enqueues; fans out.

**Supports:** Gregorian, Tithi-based, Nakshatra-based recurrence types.

**Key Logic:**
- Resolves on ≥15-month rolling horizon
- Reads Panchang cache for lunar recurrences
- Re-resolves on user location change
- Kshaya/vriddhi tithi handling per regional convention
- Fan-out to APNs/FCM/email via notification service

### 4.5 Muhurat & Planner Service

**Purpose:** "Find best date" engine.

**Logic:** Scans date range → scores candidates against event-type rules and avoidance windows → returns best/good/avoid with explanations.

**Uses:** Same engine output as daily Panchang (consistency guarantee).

### 4.6 Calendar PDF Generation Service

**Purpose:** Async 300-DPI print-ready PDF rendering.

**Design:** Queue-driven; writes to S3; returns signed download URL. Never blocks interactive app.

**Supports:** A4/A3/Letter/wall/desk; multiple templates; CMYK-ready (future).

### 4.7 AI Assistant Service ("Ask The Pandit")

**Purpose:** RAG-grounded LLM service.

**Architecture:**
```
┌──────────────────────────────────────────┐
│           AI Assistant Service            │
│                                           │
│  User Query                               │
│      │                                    │
│      ▼                                    │
│  ┌──────────┐    ┌───────────────────┐   │
│  │  Intent   │    │  Vector Store     │   │
│  │  Router   │───▶│  (CMS Corpus)     │   │
│  └──────────┘    │  Pinecone/Weaviate │   │
│      │           └────────┬──────────┘   │
│      ▼                    │               │
│  ┌──────────┐    ┌───────▼───────────┐   │
│  │ Panchang │    │  Context Builder  │   │
│  │  Cache   │───▶│  (Panchang +      │   │
│  │  Reader  │    │   Retrieved Docs) │   │
│  └──────────┘    └────────┬──────────┘   │
│                           │               │
│                  ┌───────▼───────────┐   │
│                  │   LLM (grounded)  │   │
│                  │   + Disclaimer    │   │
│                  └───────────────────┘   │
└──────────────────────────────────────────┘
```

**Rules:**
- Only grounds in Published CMS content
- Panchang data from cache, not hallucinated
- Always appends "consult a qualified pandit" disclaimer
- No free-form ritual invention
- Respects regional sensitivity

### 4.8 Content / CMS Service

**Purpose:** Editorial store and workflow for all non-astronomical content.

**Lifecycle:** Draft → In Review → Published → Archived

**Features:** Versioning, source attribution, regional tagging, review state, flag-and-review correction path.

### 4.9 User & Profile Service

**Purpose:** Accounts, auth, preferences, locations, family, role management.

**Sensitive Data:** Birth details, family birth data → encrypted Sensitive Vault (separate storage, separate access control).

### 4.10 Subscription & Billing Service

**Purpose:** Plan state (Basic/Silver/Gold), entitlement checks, receipt reconciliation.

**Integrations:**
- Apple IAP (iOS subscriptions)
- Google Play Billing (Android subscriptions)
- Stripe (web subscriptions)

**Design:** All three sources reconciled into single Subscription record. Entitlement exposed to API gateway for enforcement.

### 4.11 Pandit Marketplace Service

**Purpose:** Provider management, booking lifecycle, availability, matching.

**Sub-components:**
- Provider Registry (profiles, verification status, services, availability)
- Booking Engine (state machine, slot reservation, conflict prevention)
- Matching & Ranking (recommendation algorithm)
- Messaging (WebSocket-based, PII masking)
- Video Session Manager (SDK integration for live remote)

### 4.12 Pooja Items Marketplace Service

**Purpose:** Shopify synchronization, seller management, order tracking.

**Sub-components:**
- Shopify Sync (webhook processing, catalog overlay, fulfillment write-back)
- Seller Portal (onboarding, order management, dispatch tracking)
- Product Mapping (festival/checklist linkage)

### 4.13 Shared Platform Services

#### Payout Engine (Shared)
Single Stripe Connect integration serving both marketplaces:
- Commission calculation (configurable per marketplace/category)
- Escrow hold → release after completion + holdback
- Automated payout schedule
- Reconciliation and reporting

#### Notification Service
- Push (APNs + FCM) via fan-out
- Email (transactional + digest)
- In-app notifications
- SMS (optional)
- Delivery tracking and retry
- Quiet-hours enforcement

#### Search Service
- Full-text search across festivals, dates, tithis, content
- Natural language query parsing (LLM-assisted for Gold)
- Pandit/product search with geospatial filtering

#### Analytics Service
- Non-sensitive metrics only
- DAU/MAU, feature usage, conversion tracking
- Marketplace GMV, booking volume
- Never exposes birth details or spiritual notes

---

## 5. Data Architecture

### 5.1 Database Strategy

| Store | Technology | Purpose |
|-------|-----------|---------|
| **Primary Relational** | PostgreSQL 16+ | Users, rules, billing, bookings, content, marketplace entities |
| **Panchang Cache** | Redis Cluster | Precomputed Panchang values; key = `{date}:{locGrid}:{ayanamsa}:{scheme}` |
| **Document/Content** | PostgreSQL JSONB | CMS content with versioning; festival rules |
| **Object Storage** | S3-compatible | Generated PDFs, media, video recordings, profile images |
| **Job Queue** | Redis + Bull/BullMQ (or SQS) | PDF jobs, reminder fan-out, webhook processing, payouts |
| **Vector Store** | Pinecone or Weaviate | AI assistant RAG corpus |
| **Sensitive Vault** | PostgreSQL (encrypted tablespace) + KMS | Birth data, KYC docs, addresses — separate access control |
| **Ephemeris Data** | Filesystem | Swiss Ephemeris data files (bundled with computation service) |

### 5.2 Panchang Cache Design

**Key Structure:** `panchang:{date}:{lat_grid}:{lon_grid}:{ayanamsa}:{scheme}`

**Grid Granularity:** 0.1° lat/lon (~11km) — configurable. Nearby users share entries.

**Warming Strategy:**
1. Background job runs nightly
2. Computes ≥15 months ahead for popular locations (top 500 cities by user count)
3. Priority queue: more users → computed first
4. On cache miss: compute → store → return (lazy fill)

**TTL:** Indefinite for past dates; recomputed on engine version change.

**Size Estimate:** ~365 days × 5000 location grids × 2 schemes ≈ 3.65M entries; each ~2KB JSON ≈ 7.3GB — fits comfortably in Redis Cluster.

### 5.3 Data Partitioning Strategy

| Data | Partition Key | Rationale |
|------|--------------|-----------|
| PanchangDay cache | date + location grid | Locality of access; users access same dates/locations |
| Festival occurrences | year + region | Regional queries dominate |
| User data | user_id | Standard user-scoped access |
| Bookings | booking_id, indexed by user + pandit | Dual-access pattern |
| Orders | order_id, indexed by buyer + seller | Dual-access pattern |
| Content | entity_id + locale | Locale-scoped reads |

### 5.4 Backup & Recovery

| Concern | Target |
|---------|--------|
| **RPO (Recovery Point Objective)** | ≤1 hour for primary DB; real-time for Panchang cache (re-computable) |
| **RTO (Recovery Time Objective)** | ≤4 hours for full service restoration |
| **Backup Cadence** | Continuous WAL archival (PostgreSQL); daily full snapshots |
| **Panchang Cache Recovery** | Recompute from engine; no backup needed |
| **Cross-Region** | Primary in US-East; warm standby in EU (for GDPR residency) |

---

## 6. API Architecture

### 6.1 API Style
- **Primary:** RESTful JSON over HTTPS
- **Optional:** GraphQL for calendar grid queries (complex nested data)
- **Real-time:** WebSocket for messaging; Server-Sent Events for live booking status

### 6.2 Versioning Strategy
- **URL-based:** `/api/v1/`, `/api/v2/`
- **Policy:** Backward-compatible within major version; breaking changes only in new major version
- **Deprecation:** Minimum 6-month deprecation notice; old version supported for 12 months after new version launch
- **Migration:** Provide migration guides and change logs

### 6.3 Key API Endpoints

```
# Panchang & Calendar
GET  /api/v1/panchang/daily?date=&lat=&lon=&tz=&scheme=
GET  /api/v1/calendar/month?year=&month=&lat=&lon=
GET  /api/v1/calendar/range?from=&to=&lat=&lon=
GET  /api/v1/festivals?year=&region=&lat=&lon=
GET  /api/v1/festivals/{id}
GET  /api/v1/muhurat/find?type=&from=&to=&lat=&lon=

# User & Personal
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/profile
PUT  /api/v1/profile
CRUD /api/v1/notes
CRUD /api/v1/bookmarks
CRUD /api/v1/reminders
CRUD /api/v1/family

# Subscriptions
GET  /api/v1/subscription
POST /api/v1/subscription/verify-receipt

# Pandit Marketplace
GET    /api/v1/marketplace/pandits?service=&location=&date=
GET    /api/v1/marketplace/pandits/{id}
POST   /api/v1/marketplace/bookings
GET    /api/v1/marketplace/bookings/{id}
PATCH  /api/v1/marketplace/bookings/{id}/status
POST   /api/v1/marketplace/bookings/{id}/messages
POST   /api/v1/marketplace/bookings/{id}/review

# Provider (Pandit)
GET    /api/v1/provider/profile
PUT    /api/v1/provider/profile
CRUD   /api/v1/provider/services
PUT    /api/v1/provider/availability
GET    /api/v1/provider/bookings
GET    /api/v1/provider/earnings

# Pooja Items
GET    /api/v1/shop/products?category=&festival=
GET    /api/v1/shop/products/{id}
POST   /api/v1/shop/cart (→ Shopify Storefront)
POST   /api/v1/shop/checkout (→ Shopify Checkout)
GET    /api/v1/shop/orders

# Seller Portal
CRUD   /api/v1/seller/products
GET    /api/v1/seller/orders
POST   /api/v1/seller/orders/{id}/fulfill

# Admin
CRUD   /api/v1/admin/content
CRUD   /api/v1/admin/festivals
GET    /api/v1/admin/marketplace/*
POST   /api/v1/admin/marketplace/approve/*
GET    /api/v1/admin/analytics/*

# Calendar PDF
POST   /api/v1/calendars/generate
GET    /api/v1/calendars/jobs/{id}

# AI
POST   /api/v1/ai/ask
```

### 6.4 Rate Limiting

| Tier | Read Endpoints | Write Endpoints | Search | AI |
|------|---------------|----------------|--------|-----|
| Basic | 60/min | 20/min | 10/min | N/A |
| Silver | 120/min | 60/min | 30/min | 10/min |
| Gold | 300/min | 120/min | 60/min | 30/min |
| Admin | 600/min | 300/min | 120/min | 60/min |

### 6.5 Error Response Format

```json
{
  "error": {
    "code": "PANCHANG_LOCATION_UNSUPPORTED",
    "message": "Sunrise calculation is not available for latitudes above 66°",
    "details": { "latitude": 70.5 },
    "retry": false,
    "documentation_url": "https://docs.thepandit.app/errors/PANCHANG_LOCATION_UNSUPPORTED"
  }
}
```

**Error Taxonomy:**
- `4xx` — client errors (validation, auth, entitlement, not found)
- `5xx` — server errors (computation failure, external service down)
- Circuit breakers on external dependencies (Stripe, Shopify, KYC, LLM)

---

## 7. Event-Driven Architecture

### 7.1 Event Bus
**Technology:** AWS EventBridge (managed) or Apache Kafka (self-hosted)

**Purpose:** Decouple domain services; enable async processing; audit trail.

### 7.2 Key Event Flows

```
┌──────────────────────────────────────────────────────────┐
│                    EVENT FLOWS                            │
│                                                           │
│  BOOKING LIFECYCLE                                        │
│  booking.requested → [NotificationSvc, PayoutSvc]         │
│  booking.confirmed → [NotificationSvc, ReminderSvc,       │
│                        AvailabilitySvc]                    │
│  booking.completed → [PayoutSvc, NotificationSvc,         │
│                        ReviewSvc]                          │
│  booking.cancelled → [PayoutSvc, NotificationSvc,         │
│                        AvailabilitySvc]                    │
│  booking.disputed  → [PayoutSvc, NotificationSvc, Admin]  │
│                                                           │
│  ORDER LIFECYCLE (Pooja Items)                            │
│  shopify.order.paid     → [OrderSvc, NotificationSvc]     │
│  shopify.order.fulfilled → [PayoutSvc, NotificationSvc]   │
│  shopify.order.refunded  → [PayoutSvc, NotificationSvc]   │
│                                                           │
│  CONTENT & CACHE                                          │
│  content.published → [CacheSvc, SearchSvc, AISvc]         │
│  panchang.recomputed → [CacheSvc, FestivalSvc,            │
│                          ReminderSvc]                      │
│  festival.resolved → [CacheSvc, CalendarSvc]              │
│                                                           │
│  USER & SUBSCRIPTION                                      │
│  user.location.changed → [ReminderSvc, PanchangCache]     │
│  subscription.changed → [EntitlementSvc, NotificationSvc] │
│  user.deleted → [VaultSvc, all services (GDPR cascade)]   │
└──────────────────────────────────────────────────────────┘
```

### 7.3 Webhook Processing (External)

**Stripe Webhooks:**
- `payment_intent.succeeded`, `payment_intent.failed`
- `transfer.created`, `transfer.failed`
- `charge.dispute.created`

**Shopify Webhooks:**
- `orders/paid`, `orders/fulfilled`, `orders/cancelled`
- `refunds/create`
- `products/update`, `inventory_levels/update`

**Apple/Google:**
- Subscription receipt verification
- Subscription status changes

**Processing Pattern:**
1. Verify webhook signature
2. Check idempotency key (prevent duplicate processing)
3. Process event
4. On failure: dead-letter queue → alerting → manual review
5. Reconciliation cron runs hourly to catch missed webhooks

---

## 8. Panchang Computation Engine

### 8.1 Engine Wrapper Design

```python
# Pseudocode for the Panchang Computation Service

class PanchangComputeService:
    """
    Wraps Swiss Ephemeris. The ONLY component permitted to 
    produce raw Panchang values.
    """
    
    def compute_day(self, date, lat, lon, tz, ayanamsa, scheme):
        """
        Returns complete PanchangDay for given parameters.
        Pure, deterministic, cacheable.
        """
        # 1. Calculate sunrise/sunset (handles high-lat fallback)
        # 2. Calculate moonrise/moonset
        # 3. Calculate sun/moon longitudes at key moments
        # 4. Derive Tithi (with start/end times)
        # 5. Derive Nakshatra (with start/end times)
        # 6. Derive Yoga, Karana (with start/end times)
        # 7. Calculate muhurat windows (Rahu, Yama, Gulika, Abhijit, etc.)
        # 8. Calculate Choghadiya, Hora
        # 9. Determine Paksha, lunar month (Amanta + Purnimanta)
        # 10. Detect Adhika/Kshaya maas
        # 11. Detect kshaya/vriddhi tithi
        # 12. Format all times with 24-plus support
        # 13. Return PanchangDay object
```

### 8.2 Location Grid

**Granularity:** 0.1° lat/lon (~11km at equator)
**Rounding:** `grid_lat = round(lat, 1)`, `grid_lon = round(lon, 1)`
**Configurable:** Environment variable; can be tightened to 0.05° for accuracy-sensitive regions

### 8.3 Cache Warming Strategy

```
PRIORITY QUEUE:
1. Top 100 cities (by user count) — compute immediately
2. Top 101-500 cities — compute in batch (off-peak)
3. All user-saved locations — compute in batch
4. On-demand cache miss — compute, store, return

HORIZON: ≥15 months rolling
SCHEDULE: Nightly job (02:00 UTC)
TRIGGER: Also on engine version change (full recompute)
```

### 8.4 Validation Harness

**Reference Dataset:**
- 100+ dates × 10+ locations × 2 schemes × edge cases
- Sourced from established published Panchang (Drik Panchang / official sources)
- Covers: normal days, festival days, Adhika maas, kshaya tithi, vriddhi tithi, DST days, high-latitude locations

**CI Integration:**
- Runs on every PR to computation service
- Blocks merge on any regression beyond tolerance
- Tolerance: ±1 minute for rise/set times; exact match for tithi/nakshatra at sunrise

---

## 9. Marketplace Architecture

### 9.1 Pandit Services Marketplace

```
┌─────────────────────────────────────────────────┐
│          PANDIT MARKETPLACE SERVICE               │
│                                                   │
│  ┌───────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ Provider   │  │   Booking    │  │ Matching  │ │
│  │ Registry   │  │   Engine     │  │ & Ranking │ │
│  │            │  │              │  │           │ │
│  │ • Profile  │  │ • State FSM  │  │ • Score   │ │
│  │ • KYC      │  │ • Slot lock  │  │ • Sort    │ │
│  │ • Services │  │ • Pricing    │  │ • Geo     │ │
│  │ • Avail.   │  │ • Policy     │  │ • Anti-   │ │
│  │            │  │   snapshot   │  │   gaming  │ │
│  └───────────┘  └──────────────┘  └───────────┘ │
│                                                   │
│  ┌───────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ Messaging  │  │    Video     │  │  Review   │ │
│  │ (WebSocket)│  │   Session    │  │  Engine   │ │
│  │            │  │   Manager    │  │           │ │
│  │ • PII mask │  │ • SDK bridge │  │ • 2-way   │ │
│  │ • Persist  │  │ • Recording  │  │ • Verified│ │
│  │ • Report   │  │ • Logs       │  │ • Moderate│ │
│  └───────────┘  └──────────────┘  └───────────┘ │
└─────────────────────────────────────────────────┘
```

**Booking Slot Reservation:** Optimistic locking with retry. When a patron selects a slot:
1. Check availability (read)
2. Attempt slot lock (atomic write with version check)
3. If conflict → return "slot taken"
4. Hold slot for payment window (5 min TTL)
5. On payment success → confirm booking
6. On timeout → release slot

### 9.2 Pooja Items Marketplace

```
┌─────────────────────────────────────────────────┐
│        POOJA ITEMS MARKETPLACE SERVICE            │
│                                                   │
│  ┌───────────────────────────────────────────┐   │
│  │           Shopify Sync Layer              │   │
│  │                                            │   │
│  │  Storefront API ◄──── Web/Mobile clients  │   │
│  │  (read: products, cart, checkout)          │   │
│  │                                            │   │
│  │  Admin API ────► Shopify                   │   │
│  │  (write: fulfillment, inventory)           │   │
│  │                                            │   │
│  │  Webhooks ◄──── Shopify                    │   │
│  │  (orders, refunds, inventory changes)      │   │
│  └───────────────────────────────────────────┘   │
│                                                   │
│  ┌───────────┐  ┌──────────────┐  ┌───────────┐ │
│  │  Seller    │  │   Product    │  │  Order    │ │
│  │  Portal    │  │   Mapping    │  │  Tracker  │ │
│  │            │  │              │  │           │ │
│  │ • Onboard  │  │ • Festival   │  │ • Split   │ │
│  │ • KYC      │  │   linkage    │  │ • Status  │ │
│  │ • Orders   │  │ • Checklist  │  │ • Return  │ │
│  │ • Dispatch │  │   linkage    │  │ • Dispute │ │
│  └───────────┘  └──────────────┘  └───────────┘ │
└─────────────────────────────────────────────────┘
```

### 9.3 Shared Payout Engine

```
┌─────────────────────────────────────────────────┐
│              PAYOUT ENGINE (shared)                │
│                                                   │
│  Input: Booking/Order completion event            │
│    │                                              │
│    ▼                                              │
│  ┌─────────────────────────────────────────┐     │
│  │ Commission Calculator                    │     │
│  │ • Per-marketplace rate config            │     │
│  │ • Per-category overrides                 │     │
│  │ • Pass-through items (travel, shipping)  │     │
│  └────────────────┬────────────────────────┘     │
│                   │                               │
│                   ▼                               │
│  ┌─────────────────────────────────────────┐     │
│  │ Holdback Timer                           │     │
│  │ • Configurable per marketplace           │     │
│  │ • Dispute window check                   │     │
│  └────────────────┬────────────────────────┘     │
│                   │                               │
│                   ▼                               │
│  ┌─────────────────────────────────────────┐     │
│  │ Stripe Connect Transfer                  │     │
│  │ • Idempotency key                        │     │
│  │ • Retry with backoff                     │     │
│  │ • Reconciliation                         │     │
│  └─────────────────────────────────────────┘     │
└─────────────────────────────────────────────────┘
```

---

## 10. Mobile & Web Client Architecture

### 10.1 Web App (Next.js)

```
src/
├── app/                    # Next.js App Router
│   ├── (auth)/             # Auth routes
│   ├── (main)/             # Main app routes
│   │   ├── today/          # Daily Panchang (SSR)
│   │   ├── calendar/       # Calendar views
│   │   ├── festivals/      # Festival pages (SSR for SEO)
│   │   ├── planner/        # Muhurat & planning
│   │   ├── marketplace/    # Pandit services
│   │   ├── shop/           # Pooja items (Shopify Storefront)
│   │   └── profile/        # User settings
│   └── admin/              # Admin console
├── components/             # Shared UI components
│   ├── panchang/           # Panchang display components
│   ├── calendar/           # Calendar grid (virtualized)
│   ├── marketplace/        # Marketplace UI
│   └── shared/             # Design system components
├── lib/                    # Business logic
│   ├── api/                # API client
│   ├── cache/              # Client-side caching
│   └── shopify/            # Storefront API client
└── styles/                 # Tailwind config + themes
    ├── devotional.css      # Consumer theme (saffron/gold)
    └── aqualeo.css         # Admin theme (dark/aqua)
```

### 10.2 Mobile App Architecture

```
Platform/
├── Core/                   # Shared business logic
│   ├── API/                # API client + auth
│   ├── Cache/              # Local DB (SQLite/CoreData)
│   ├── Models/             # Data models
│   └── Sync/               # Background sync + offline
├── Features/               # Feature modules
│   ├── Panchang/           # Daily view
│   ├── Calendar/           # Calendar views
│   ├── Festivals/          # Festival detail
│   ├── Reminders/          # Notification scheduling
│   ├── Marketplace/        # Pandit booking
│   ├── Shop/               # Pooja items (Shopify SDK)
│   └── Profile/            # Settings
├── Widgets/                # Home/lock-screen widgets
└── Push/                   # Push notification handling
```

### 10.3 Offline Strategy

| Data | Strategy | Sync |
|------|----------|------|
| Current month Panchang | Prefetch on app open | Background refresh daily |
| Recently viewed days | LRU cache (last 30 days) | On next access |
| Notes & Bookmarks | Local-first, sync on connectivity | Conflict: server-wins with version vectors |
| Downloaded calendars | Persist until deleted | No sync needed |
| Festival details | Cache last 20 viewed | On next access |
| Panchang cache | Never offline-computed | Server is source of truth |

---

## 11. Security Architecture

### 11.1 Authentication Flow

```
┌──────────┐         ┌──────────┐         ┌──────────┐
│  Client   │         │ API GW   │         │ Auth Svc │
│           │──OAuth──▶│          │──verify─▶│ (OIDC)   │
│           │◀─JWT────│          │◀─tokens─│          │
│           │         │          │         │          │
│           │──API────▶│          │         │          │
│           │         │ JWT      │         │          │
│           │         │ validate │         │          │
│           │         │ + tier   │         │          │
│           │         │ check    │         │          │
└──────────┘         └──────────┘         └──────────┘
```

### 11.2 Sensitive Data Vault

```
┌────────────────────────────────────────────┐
│           SENSITIVE DATA VAULT              │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │  Encrypted at Rest (AES-256-GCM)    │   │
│  │  Key Management: AWS KMS / Vault    │   │
│  │                                      │   │
│  │  • User birth date/time/place       │   │
│  │  • Family member birth details      │   │
│  │  • Pandit KYC documents             │   │
│  │  • Seller KYC documents             │   │
│  │  • Patron ceremony addresses        │   │
│  │  • Background check references      │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ACCESS CONTROL:                            │
│  • Separate IAM role required               │
│  • Every access logged with purpose         │
│  • Excluded from analytics queries          │
│  • Excluded from backups to non-secure      │
│  • Addresses revealed only after paid       │
│    booking (time-limited access)            │
│  • GDPR delete cascades here first          │
└────────────────────────────────────────────┘
```

### 11.3 RBAC Model

| Role | Scope | Access |
|------|-------|--------|
| User (Basic) | Own profile, limited features | Read Panchang, limited CRUD |
| User (Silver) | Own profile, expanded features + marketplace | Full CRUD, marketplace checkout |
| User (Gold) | All features | Full CRUD, AI, advanced features |
| Pandit | Own provider profile + bookings | Provider CRUD, booking management |
| Seller | Own shop + orders | Product CRUD, order fulfillment |
| Admin (Content) | CMS | Content CRUD, review workflow |
| Admin (Ops) | Marketplace | Approve/suspend, disputes |
| Admin (Finance) | Payouts | Reports, reconciliation |
| Admin (Super) | Everything | Full access, config, audit |

---

## 12. Scalability & Performance

### 12.1 Scaling Strategy

| Component | Scaling Pattern | Trigger |
|-----------|----------------|---------|
| API Gateway | Horizontal auto-scale | CPU > 70% or requests/sec |
| Panchang Cache (Redis) | Cluster scaling | Memory > 80% |
| Computation Service | Horizontal (stateless) | Queue depth |
| PDF Generation | Queue-based, horizontal workers | Queue depth |
| Web App (Next.js) | Horizontal + CDN | Response time |
| PostgreSQL | Read replicas + connection pooling | Query latency |
| Notification Fan-out | Queue-based workers | Queue depth |

### 12.2 CDN Strategy

| Content | CDN | TTL |
|---------|-----|-----|
| Panchang API responses (by location) | CloudFront / Cloudflare | 1 hour (invalidate on recompute) |
| Festival content (by locale) | CDN | 24 hours |
| Static assets (images, CSS, JS) | CDN | 30 days |
| Generated calendar PDFs | S3 + signed URLs | No CDN (private) |
| CMS images | CDN | 7 days |

### 12.3 Festival Spike Preparation

Major festivals (Diwali, Navratri, etc.) can cause 10-50x traffic:
1. **Pre-warm caches** 7 days before major festivals for all popular locations
2. **Auto-scale** API and web tier based on traffic forecast
3. **Stagger notifications** — don't fire millions of festival reminders at the same second
4. **CDN cache** festival detail pages (they're read-heavy, rarely change)

---

## 13. Observability & Operations

### 13.1 Monitoring Stack

| Layer | Tool | Metrics |
|-------|------|---------|
| Infrastructure | CloudWatch / Datadog | CPU, memory, disk, network |
| Application | OpenTelemetry + Jaeger | Request traces, latency, error rates |
| Business | Custom dashboards | DAU, conversions, GMV, bookings |
| Panchang | Custom | Cache hit rate, miss rate, computation time |
| Payments | Custom + Stripe Dashboard | Success rate, failed payouts, disputes |

### 13.2 SLOs

| Service | Metric | Target |
|---------|--------|--------|
| Panchang read (cached) | p99 latency | < 200ms |
| Panchang read (miss) | p99 latency | < 2000ms |
| Calendar view | p99 latency | < 500ms |
| Festival search | p99 latency | < 300ms |
| Pandit search | p99 latency | < 1000ms |
| Booking creation | p99 latency | < 2000ms |
| API availability | Uptime | 99.9% monthly |
| Push notification delivery | Success rate | > 98% |

### 13.3 Alerting

| Alert | Condition | Severity |
|-------|-----------|----------|
| Cache miss rate spike | > 10% miss rate for 5 min | P1 |
| Payment failure spike | > 5% failure rate for 10 min | P0 |
| Payout stuck | Payout pending > 72 hours | P1 |
| API error rate | > 1% 5xx for 5 min | P1 |
| Queue backlog | > 10,000 items for 15 min | P2 |
| Webhook gap | No Shopify webhook for > 1 hour | P1 |
| Video join failure | > 20% join failure rate | P1 |

---

## 14. Deployment Architecture

### 14.1 Infrastructure

**Primary:** AWS (or GCP/Azure — cloud-agnostic design where possible)

```
┌─────────────────────────────────────────────────────┐
│                    AWS DEPLOYMENT                     │
│                                                       │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │ CloudFront   │  │   ALB        │  │ Route 53    │ │
│  │ (CDN)        │  │ (Load Bal.)  │  │ (DNS)       │ │
│  └──────┬──────┘  └──────┬───────┘  └─────────────┘ │
│         │                │                            │
│  ┌──────▼──────────────▼────────────────────────┐   │
│  │           ECS Fargate / EKS                   │   │
│  │                                                │   │
│  │  API Gateway │ Web (Next.js) │ Admin (React)  │   │
│  │  Panchang Compute │ Calendar │ Festival       │   │
│  │  Marketplace │ CMS │ Users │ Billing          │   │
│  │  Payout │ Notification │ AI │ Search           │   │
│  └──────────────────────────────────────────────┘   │
│                                                       │
│  ┌────────┐ ┌────────┐ ┌───────┐ ┌────────────────┐ │
│  │ RDS    │ │ Redis  │ │ S3    │ │ SQS/EventBridge│ │
│  │ (PG)   │ │Cluster │ │       │ │                │ │
│  └────────┘ └────────┘ └───────┘ └────────────────┘ │
│                                                       │
│  ┌────────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ KMS        │  │ Secrets  │  │ CloudWatch +     │ │
│  │ (Vault     │  │ Manager  │  │ OpenTelemetry    │ │
│  │  encryption)│  │          │  │                  │ │
│  └────────────┘  └──────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### 14.2 Environment Strategy

| Environment | Purpose | Infrastructure |
|-------------|---------|---------------|
| Local Dev | Developer machines | Docker Compose |
| CI/CD | Automated testing | GitHub Actions + ephemeral containers |
| Staging | Pre-production validation | Scaled-down production clone |
| Production | Live service | Full infrastructure |

### 14.3 CI/CD Pipeline

```
Code Push → Lint/Format → Unit Tests → Panchang Validation Harness
  → Integration Tests → Build Containers → Deploy to Staging
  → Smoke Tests → Manual Approval → Deploy to Production
  → Canary (10%) → Full Rollout
```

---

## 15. Technology Stack Decisions

| Concern | Choice | Rationale |
|---------|--------|-----------|
| **Web Client** | Next.js 14+ / Tailwind / TypeScript | SSR for SEO; shared types with API; Aqualeo design system |
| **Mobile (iOS)** | Swift / SwiftUI | Native widgets, lock-screen; best iOS experience |
| **Mobile (Android)** | Kotlin / Jetpack Compose | Native widgets; modern Android |
| **Admin Console** | React / Tailwind / TypeScript | Shared component library with web |
| **API Gateway** | Express/Fastify (Node.js) or API Gateway (AWS) | Lightweight; handles auth/rate-limit/routing |
| **Backend Services** | Python (computation); TypeScript/Node.js (business services) | Python for Swiss Ephemeris binding; TS for shared web types |
| **Panchang Engine** | Swiss Ephemeris via `pyswisseph` | Gold standard; C-extension for performance |
| **Primary Database** | PostgreSQL 16+ | Relational integrity; JSONB for flexible content |
| **Cache** | Redis Cluster | Panchang cache; session cache; job queues |
| **Object Storage** | AWS S3 | PDFs, media, recordings |
| **Job Queue** | BullMQ (Redis-backed) or SQS | PDF jobs, reminder fan-out, webhook processing |
| **Event Bus** | AWS EventBridge | Managed; serverless; event routing |
| **Push Notifications** | APNs + FCM via SNS | Managed fan-out; delivery tracking |
| **Vector Store** | Pinecone (managed) or Weaviate | AI RAG corpus |
| **LLM** | OpenAI GPT-4 / Claude (via API) | Grounded AI assistant |
| **Payments (Subs)** | Apple IAP + Google Play Billing + Stripe | Platform compliance |
| **Payments (Marketplace)** | Stripe Connect | Escrow, commission, payouts |
| **E-commerce** | Headless Shopify + Storefront API | Catalog, cart, checkout, tax, PCI |
| **KYC** | Stripe Identity / Onfido | ID verification, background checks |
| **Video** | Agora / Twilio Video / LiveKit (evaluate) | Live 1:1 remote ceremonies |
| **CDN** | CloudFront / Cloudflare | Global distribution |
| **Monitoring** | OpenTelemetry + CloudWatch + Datadog | Traces, metrics, logs |
| **IaC** | Terraform / Pulumi | Reproducible infrastructure |

---

## 16. Architecture Decision Records

### ADR-001: Drik Ganita over Vakya for Panchang Computation
**Status:** Accepted
**Context:** Need to choose between traditional Vakya and observational Drik Ganita methods.
**Decision:** Drik Ganita via Swiss Ephemeris.
**Consequences:** Higher accuracy; matches published Panchangs; requires licensing for commercial use.

### ADR-002: Precompute-and-Cache over Live Computation
**Status:** Accepted
**Context:** Panchang data needed by multiple consumers (calendar, festivals, reminders, muhurat).
**Decision:** Precompute and cache; clients never compute.
**Consequences:** Consistency guaranteed; 2-second load target achievable; cache warming cost; ~7GB Redis footprint.

### ADR-003: Headless Shopify for E-Commerce
**Status:** Accepted
**Context:** Need product catalog, cart, checkout, PCI compliance, tax calculation for pooja items.
**Decision:** Use headless Shopify; sellers managed through platform portal.
**Consequences:** Avoids building commerce from scratch; Shopify subscription cost; vendor dependency; well-tested PCI compliance.

### ADR-004: Stripe Connect for Unified Payouts
**Status:** Accepted
**Context:** Both marketplaces need escrow, commission, and seller/pandit payouts.
**Decision:** Single Stripe Connect integration serving both.
**Consequences:** One payout system; Stripe fees; proven escrow model; multi-currency support.

### ADR-005: Event-Driven Service Communication
**Status:** Accepted
**Context:** Multiple services need to react to booking/order/content state changes.
**Decision:** AWS EventBridge as event bus; services publish and subscribe to domain events.
**Consequences:** Loose coupling; async processing; eventual consistency; need for idempotent handlers.

### ADR-006: Native Mobile over Cross-Platform
**Status:** Under Discussion
**Context:** Need iOS and Android apps with widget/lock-screen support.
**Decision:** Native Swift + Kotlin recommended; React Native/Flutter as fallback if team skills favor it.
**Consequences:** Best widget experience with native; higher dev cost; or shared codebase with cross-platform but potential widget limitations.

### ADR-007: Location Grid at 0.1° Granularity
**Status:** Accepted
**Context:** Need to balance cache efficiency with sunrise accuracy.
**Decision:** 0.1° lat/lon (~11km), configurable.
**Consequences:** ~5000 grid cells for popular locations; sunrise accuracy within ~1 minute; configurable for tightening.

---

*End of Refined Architecture Document v2.0*
