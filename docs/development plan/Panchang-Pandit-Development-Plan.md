# The Pandit — Phased Development Plan

**Version:** 2.0
**Date:** July 2026
**Priority:** Web app first → Mobile apps as final target
**Strategy:** Maximum parallel development; modular delivery

---

## Executive Summary

This plan organizes the development of **The Pandit** into 6 phases, structured for web-first delivery with mobile as the final target. Each phase identifies parallel work streams, dependencies, and includes **specific Claude Sonnet prompts** that can be used directly for implementation.

---

## Table of Contents

1. [Development Philosophy](#1-development-philosophy)
2. [Phase Overview](#2-phase-overview)
3. [Phase 0: Foundation & Infrastructure](#3-phase-0-foundation--infrastructure)
4. [Phase 1: Core Panchang MVP (Web)](#4-phase-1-core-panchang-mvp-web)
5. [Phase 2: Enhanced Features (Web)](#5-phase-2-enhanced-features-web)
6. [Phase 3: Premium & AI Features (Web)](#6-phase-3-premium--ai-features-web)
7. [Phase 4: Marketplaces (Web)](#7-phase-4-marketplaces-web)
8. [Phase 5: Mobile Apps](#8-phase-5-mobile-apps)
9. [Parallel Development Matrix](#9-parallel-development-matrix)
10. [Risk Register & Mitigation](#10-risk-register--mitigation)
11. [Launch Gates](#11-launch-gates)

---

## 1. Development Philosophy

### 1.1 Principles
1. **Web first** — the responsive web app is the primary platform; mobile apps wrap the same API
2. **API-first** — build the backend API; web and mobile are consumers
3. **Panchang engine first** — everything depends on it; validate accuracy before building features
4. **Parallel where independent** — identify modules that share no dependencies and build concurrently
5. **Ship incrementally** — each phase is deployable and provides user value
6. **Test accuracy obsessively** — the Panchang validation harness is Phase 0, not Phase N

### 1.2 Team Structure (Recommended)

| Stream | Skills | Phases Active |
|--------|--------|---------------|
| **Engine Team** (1-2 devs) | Python, astronomy, Swiss Ephemeris | 0-1 |
| **Backend Team** (2-3 devs) | Node.js/TypeScript, PostgreSQL, Redis, APIs | 0-5 |
| **Web Frontend Team** (2 devs) | Next.js, React, Tailwind, TypeScript | 1-4 |
| **Mobile Team** (2 devs) | Swift/SwiftUI, Kotlin/Compose | 5 |
| **Content Team** (1-2 people) | Hindu calendar knowledge, writing, translation | 1-5 |
| **DevOps** (1 dev) | AWS, Terraform, CI/CD, monitoring | 0-5 |

---

## 2. Phase Overview

```
PHASE 0 ──── Foundation & Infrastructure ──── 3-4 weeks
    │
PHASE 1 ──── Core Panchang MVP (Web) ──────── 8-10 weeks
    │
PHASE 2 ──── Enhanced Features (Web) ────── 6-8 weeks
    │
PHASE 3 ──── Premium & AI Features (Web) ── 6-8 weeks
    │
PHASE 4 ──── Marketplaces (Web) ──────────── 10-12 weeks
    │
PHASE 5 ──── Mobile Apps (iOS + Android) ── 8-10 weeks
```

**Total estimated timeline: 41-52 weeks** (with parallel streams)

**With aggressive parallelism: 30-38 weeks** (see §9)

---

## 3. Phase 0: Foundation & Infrastructure

**Duration:** 3-4 weeks
**Goal:** Set up infrastructure, establish the Panchang computation engine, build the validation harness
**Parallel Streams:** 3 (fully independent)

### Stream 0A: Infrastructure Setup (DevOps)

**Complexity:** Medium | **Dependencies:** None

**Tasks:**
- [ ] Set up AWS account structure (dev, staging, prod)
- [ ] Configure Terraform/Pulumi for IaC
- [ ] Set up PostgreSQL (RDS), Redis (ElastiCache), S3
- [ ] Configure CI/CD pipeline (GitHub Actions)
- [ ] Set up monitoring stack (CloudWatch + OpenTelemetry)
- [ ] Configure CDN (CloudFront)
- [ ] Set up secret management (AWS Secrets Manager)
- [ ] Create Docker Compose for local development
- [ ] Configure EventBridge (event bus)

#### Claude Prompt — Infrastructure Setup

```
You are setting up AWS infrastructure for "The Pandit", a Hindu Panchang 
and calendar application. Create Terraform/Pulumi configuration for:

1. VPC with public/private subnets across 2 AZs
2. RDS PostgreSQL 16 instance (db.t3.medium for dev, with read replica config ready)
3. ElastiCache Redis Cluster (cache.t3.medium, cluster mode enabled)
4. S3 bucket for generated calendars and media (with lifecycle policies)
5. SQS queues: pdf-generation, reminder-fanout, webhook-processing
6. EventBridge event bus named "thepandit-events" with rules for:
   - booking.* → SQS notifications queue
   - panchang.recomputed → SQS cache-invalidation queue
7. CloudFront distribution with origins for:
   - Next.js web app (ALB origin)
   - S3 media bucket
   - API gateway (with /api/* path pattern)
8. Secrets Manager entries for: database URL, Redis URL, Stripe keys, 
   Shopify keys, Swiss Ephemeris config
9. ECS Fargate cluster with service definitions for:
   - api-gateway (port 3000)
   - panchang-compute (port 8000, Python)
   - web-app (port 3001, Next.js)
10. IAM roles with least-privilege for each service
11. KMS key for the Sensitive Data Vault encryption

Include a docker-compose.yml for local development that mirrors this setup
with local PostgreSQL, Redis, LocalStack (S3, SQS, EventBridge), and 
the Panchang computation service.

Output as modular Terraform files with clear comments.
```

### Stream 0B: Panchang Computation Engine (Engine Team)

**Complexity:** Very High | **Dependencies:** None

**Tasks:**
- [ ] Set up Python project with `pyswisseph` binding
- [ ] Implement sunrise/sunset calculation (location-aware)
- [ ] Implement moonrise/moonset calculation
- [ ] Implement Tithi calculation with start/end times
- [ ] Implement Nakshatra calculation with start/end times
- [ ] Implement Yoga and Karana calculations
- [ ] Implement Paksha and lunar month determination (Amanta + Purnimanta)
- [ ] Implement Rahu Kalam, Yamaganda, Gulika calculations
- [ ] Implement Abhijit Muhurat, Choghadiya, Hora
- [ ] Implement Adhika/Kshaya maas detection
- [ ] Implement Kshaya/Vriddhi tithi detection
- [ ] Implement high-latitude fallback
- [ ] Implement DST transition handling
- [ ] Implement 24-plus time format
- [ ] Implement Samvat calculations (Vikram, Shaka, Gujarati)
- [ ] Build REST API wrapper (FastAPI)
- [ ] Create comprehensive test suite

#### Claude Prompt — Panchang Engine Core

```
You are building the Panchang Computation Service for "The Pandit" app.
This is a Python FastAPI service that wraps Swiss Ephemeris (pyswisseph)
to calculate Hindu Panchang data.

CRITICAL REQUIREMENTS:
- This is the SINGLE SOURCE OF TRUTH for all astronomical calculations
- All values must have precise start/end times
- The Hindu day runs sunrise-to-sunrise (not midnight-to-midnight)
- Must handle Lahiri (Chitrapaksha) ayanamsa as default with override option
- Must support both Amanta and Purnimanta month schemes

Create a Python project with:

1. `panchang/engine.py` — Core computation class:
   - Method: `compute_day(date, lat, lon, tz, ayanamsa='lahiri', scheme='amanta')`
   - Returns a PanchangDay dataclass with ALL of:
     * sunrise, sunset, moonrise, moonset (with location-aware calc)
     * tithi (name, number, start_time, end_time, paksha)
     * nakshatra (name, number, start_time, end_time)
     * yoga (name, start_time, end_time)
     * karana (name, start_time, end_time) — both karanas of the day
     * vara (weekday)
     * lunar_month (amanta_month, purnimanta_month, is_adhika_maas)
     * rahu_kalam (start, end)
     * yamaganda (start, end)
     * gulika_kalam (start, end)
     * abhijit_muhurat (start, end)
     * brahma_muhurat (start, end)
     * samvat (vikram, shaka, gujarati)
     * ritu, ayana, samvatsara

2. `panchang/edge_cases.py` — Edge case handlers:
   - Adhika maas (leap lunar month) detection
   - Kshaya maas (skipped month) detection
   - Kshaya tithi (tithi never spans a sunrise)
   - Vriddhi tithi (tithi spans two sunrises)
   - High latitude fallback (lat > 66°)
   - DST transition mid-tithi handling
   - 24-plus time representation (past midnight in sunrise-day)

3. `panchang/api.py` — FastAPI endpoints:
   - GET /compute?date=YYYY-MM-DD&lat=&lon=&tz=&ayanamsa=&scheme=
   - GET /compute/range?from=&to=&lat=&lon=&tz= (batch)
   - GET /health

4. `tests/test_engine.py` — Test suite with known-good values:
   - Test against Drik Panchang reference for at least 10 dates across 
     5 locations (Mumbai, Delhi, New York, London, Dubai)
   - Test Adhika maas detection
   - Test kshaya/vriddhi tithi
   - Test DST transition (US spring-forward, fall-back)
   - Test high latitude (Reykjavik, Tromsø)
   - Test both Amanta and Purnimanta for the same date

Use pyswisseph for all astronomical calculations. The Tithi is calculated
as: tithi_number = floor((moon_longitude - sun_longitude) / 12) + 1
where longitudes are sidereal (after applying ayanamsa correction).

Sunrise calculation must use the Swiss Ephemeris sunrise function with 
atmospheric refraction. For high latitudes where sunrise is undefined, 
use civil twilight as fallback.

Include a requirements.txt with: pyswisseph, fastapi, uvicorn, pydantic,
python-dateutil, pytz.
```

### Stream 0C: Database Schema & Validation Harness (Backend Team)

**Complexity:** High | **Dependencies:** None

**Tasks:**
- [ ] Design and implement core database schema (PostgreSQL)
- [ ] Build Panchang validation harness
- [ ] Create reference dataset from established Panchang
- [ ] Integrate validation into CI pipeline
- [ ] Set up database migration framework (Alembic or Prisma)

#### Claude Prompt — Database Schema

```
Create the PostgreSQL database schema for "The Pandit" Hindu Panchang app.
Use a migration framework (either Prisma schema or Alembic/SQLAlchemy).

Create these tables with proper relationships, indexes, and constraints:

CORE TABLES:
1. users (id UUID PK, email, phone, display_name, preferred_locale, 
   preferred_scheme ENUM('amanta','purnimanta'), preferred_ayanamsa, 
   preferred_calendar_style, subscription_tier ENUM('basic','silver','gold'),
   roles TEXT[] — supports ['user','pandit','seller','admin'],
   created_at, updated_at)

2. sensitive_vault (id UUID PK, user_id FK UNIQUE, dob_encrypted, 
   tob_encrypted, pob_encrypted, family_data_encrypted, 
   encryption_key_id, accessed_at, created_at)
   — This table uses column-level encryption via pgcrypto

3. locations (id UUID PK, user_id FK, label, lat DECIMAL(9,6), 
   lon DECIMAL(9,6), timezone, dst_rule, is_primary BOOLEAN, created_at)

4. panchang_cache (id BIGSERIAL PK, date DATE, location_grid_key VARCHAR,
   ayanamsa VARCHAR, scheme VARCHAR, data JSONB, computed_at,
   engine_version VARCHAR,
   UNIQUE(date, location_grid_key, ayanamsa, scheme))

5. festival_rules (id UUID PK, name VARCHAR, identifier VARCHAR UNIQUE,
   anga_rule JSONB, scheme VARCHAR, region_tags TEXT[], deity VARCHAR,
   priority INT, is_active BOOLEAN, created_at, updated_at)

6. festival_occurrences (id BIGSERIAL PK, festival_rule_id FK, date DATE,
   location_grid_key VARCHAR, year INT, resolved_at,
   UNIQUE(festival_rule_id, date, location_grid_key))

7. festival_content (id UUID PK, festival_id FK, locale VARCHAR,
   title, description TEXT, significance TEXT, puja_method TEXT,
   katha TEXT, mantras TEXT, samagri_list JSONB, regional_variations JSONB,
   review_state ENUM('draft','in_review','published','archived'),
   version INT, author VARCHAR, source_attribution TEXT,
   created_at, updated_at)

8. reminders (id UUID PK, user_id FK, title, recurrence_type 
   ENUM('gregorian','tithi','nakshatra','weekday','festival'),
   recurrence_spec JSONB, next_fire_time TIMESTAMPTZ, location_id FK,
   offset_minutes INT, is_active BOOLEAN, created_at)

9. notes (id UUID PK, user_id FK, date_ref_gregorian DATE,
   date_ref_tithi JSONB, category VARCHAR, body TEXT, created_at, updated_at)

10. bookmarks (id UUID PK, user_id FK, date_ref DATE, 
    date_ref_tithi JSONB, category VARCHAR, created_at)

11. family_members (id UUID PK, user_id FK, name, relation,
    birth_tithi JSONB, birth_nakshatra VARCHAR, gotra VARCHAR,
    — actual birth date/time stored in sensitive_vault
    created_at)

12. vrat_records (id UUID PK, user_id FK, vrat_type VARCHAR,
    date DATE, status ENUM('planned','observed','missed','completed'),
    sankalp TEXT, notes TEXT, created_at, updated_at)

13. calendar_jobs (id UUID PK, user_id FK, template VARCHAR,
    start_month DATE, duration_months INT, location_id FK,
    language VARCHAR, status ENUM('queued','processing','completed','failed'),
    output_url TEXT, created_at, completed_at)

14. subscriptions (id UUID PK, user_id FK UNIQUE, tier, source 
    ENUM('apple','google','stripe'), status ENUM('active','cancelled',
    'expired','grace_period'), stripe_subscription_id, apple_receipt,
    google_purchase_token, expires_at, created_at, updated_at)

15. content_versions (id UUID PK, entity_type, entity_id UUID,
    version INT, author, review_state, source_attribution, diff JSONB,
    created_at)

INDEXES:
- panchang_cache: (date, location_grid_key, ayanamsa, scheme) — already UNIQUE
- festival_occurrences: (date, location_grid_key), (year, festival_rule_id)
- reminders: (user_id, is_active, next_fire_time)
- notes: (user_id, date_ref_gregorian)
- festival_content: (festival_id, locale, review_state)

Include seed data migration with 5 sample festival rules:
- Diwali (Kartik Amavasya), Holi (Phalguna Purnima), 
- Ganesh Chaturthi (Bhadrapada Shukla 4), Navratri (Ashwin Shukla 1-9),
- Maha Shivaratri (Magha Krishna 14)

Output as SQL migration files or Prisma schema.
```

#### Claude Prompt — Validation Harness

```
Create a Panchang validation harness for "The Pandit" that runs in CI
and blocks merges on any accuracy regression.

The harness:
1. Maintains a reference dataset in JSON/YAML with known-good Panchang 
   values sourced from established published Panchangs (Drik Panchang).

2. Reference dataset structure — for each test case:
   {
     "date": "2026-01-14",
     "location": {"lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata"},
     "ayanamsa": "lahiri",
     "expected": {
       "sunrise": "07:14",
       "sunset": "17:41",
       "tithi": {"name": "Purnima", "number": 15},
       "nakshatra": {"name": "Pushya", "number": 8},
       "paksha": "Shukla",
       "lunar_month_amanta": "Paush",
       "is_adhika_maas": false,
       "rahu_kalam": {"start": "10:45", "end": "12:07"}
     },
     "tolerance": {"time_minutes": 2, "tithi_at_sunrise": "exact"}
   }

3. Create test cases covering:
   - 20 normal dates across 10 locations worldwide
   - 5 Adhika maas dates
   - 3 Kshaya tithi dates
   - 3 Vriddhi tithi dates
   - 2 DST transition dates (US)
   - 2 high-latitude dates (above 60°N)
   - 5 major festival dates (verify correct tithi resolution)

4. Assertion logic:
   - Time values: within tolerance (default ±2 minutes)
   - Tithi/Nakshatra at sunrise: exact match
   - Adhika/Kshaya maas detection: exact match
   - Paksha: exact match

5. CI integration:
   - pytest-based test runner
   - Runs on every PR to the panchang-compute service
   - Blocks merge on ANY failure
   - Generates a human-readable accuracy report

Create the Python test framework, sample reference data (fill with
realistic values for Mumbai, Delhi, New York, London, Dubai, Singapore,
Sydney, Toronto, Los Angeles, Reykjavik), and a GitHub Actions workflow
that runs it.
```

---

## 4. Phase 1: Core Panchang MVP (Web)

**Duration:** 8-10 weeks
**Goal:** Launch a working web app with daily Panchang, calendar views, festivals, notes, bookmarks, reminders, and basic subscription
**Parallel Streams:** 4

### Stream 1A: Backend API Services (Backend Team)

**Complexity:** High | **Dependencies:** Phase 0 (schema, engine)

**Tasks:**
- [ ] API Gateway setup (authentication, rate limiting, routing)
- [ ] Panchang caching layer (Redis integration with warming job)
- [ ] Calendar Assembly service (day/week/month/year views)
- [ ] Festival Rule Engine (rule definition → occurrence resolution)
- [ ] Notes/Bookmarks/Reminders CRUD API
- [ ] Basic reminder scheduler (Gregorian-only for MVP; Tithi in Phase 2)
- [ ] User registration/auth (OAuth/OIDC for Google, Apple, email)
- [ ] Basic subscription service (tier check, receipt verification stub)
- [ ] Notification service (push via FCM, basic email)
- [ ] Content API (read-only for festivals/educational content)

#### Claude Prompt — Backend API

```
Build the backend API for "The Pandit" Hindu Panchang app using 
TypeScript/Node.js with Express or Fastify.

Project structure:
```
src/
├── config/              # Environment, database, redis config
├── middleware/           # Auth, rate-limit, entitlement, error handler
├── routes/              # Route definitions
│   ├── panchang.ts      # GET /api/v1/panchang/daily, /range
│   ├── calendar.ts      # GET /api/v1/calendar/day, /week, /month, /year
│   ├── festivals.ts     # GET /api/v1/festivals, /:id
│   ├── notes.ts         # CRUD /api/v1/notes
│   ├── bookmarks.ts     # CRUD /api/v1/bookmarks
│   ├── reminders.ts     # CRUD /api/v1/reminders
│   ├── auth.ts          # POST /register, /login, /refresh
│   ├── profile.ts       # GET/PUT /api/v1/profile
│   └── subscription.ts  # GET /api/v1/subscription
├── services/
│   ├── panchang-cache.ts    # Redis cache layer over compute service
│   ├── calendar-assembly.ts # Compose views from cache + user data
│   ├── festival-engine.ts   # Rule resolution engine
│   ├── reminder-scheduler.ts # Resolve & schedule reminders
│   ├── notification.ts      # Push + email fan-out
│   ├── auth.ts              # OAuth/OIDC (Google, Apple, email/password)
│   └── subscription.ts     # Tier management, receipt verification
├── models/              # TypeScript types/interfaces for all entities
├── db/                  # Database client (Prisma or TypeORM)
├── queue/               # Job queue workers (BullMQ)
└── utils/               # Helpers, validators, error types
```

KEY IMPLEMENTATION DETAILS:

1. PANCHANG CACHE SERVICE:
   - Reads from Redis first (key: panchang:{date}:{grid_lat}:{grid_lon}:{ayanamsa}:{scheme})
   - On miss: calls the Python Panchang Compute Service HTTP API
   - Stores result in Redis (no TTL for past dates)
   - Grid rounding: lat/lon rounded to 1 decimal place
   - Warming job: runs nightly, computes 15 months ahead for top locations

2. CALENDAR ASSEMBLY:
   - GET /api/v1/calendar/month?year=2026&month=7&lat=28.6&lon=77.2
   - Returns array of 28-31 days, each with:
     * panchang data (from cache), festival markers, user notes, 
       bookmarks, reminders for that day
   - Must be efficient: batch-fetch 30 days from Redis in one MGET

3. FESTIVAL ENGINE:
   - Each festival is a rule (JSONB): 
     {"tithi": 15, "paksha": "shukla", "month": "kartik", "scheme": "amanta"}
   - Resolver reads panchang cache for each day in the year
   - Finds the day where the specified tithi is active at sunrise
   - Stores results in festival_occurrences table
   - Handles Amanta/Purnimanta month shift
   - Batch-resolve all festivals for a year+location on first request, cache

4. AUTH:
   - Google OAuth2 + Apple Sign-In (OIDC)
   - Email/password with bcrypt
   - JWT access tokens (15 min) + refresh tokens (30 days)
   - Guest mode: auto-created anonymous user, upgradeable

5. ENTITLEMENT MIDDLEWARE:
   - Reads user's subscription tier from JWT claims
   - Enforces feature gates: 
     Basic: 5 notes, 5 bookmarks, 5 reminders, current year only
     Silver: unlimited, advanced features
     Gold: all features, AI
   - Returns 403 with upgrade prompt for gated features

6. RATE LIMITING:
   - express-rate-limit or fastify-rate-limit
   - Per tier limits (Basic: 60/min, Silver: 120/min, Gold: 300/min)
   - Key by user ID (authenticated) or IP (anonymous)

Include comprehensive error handling with typed errors, request 
validation (zod or joi), and structured logging (pino).

Output TypeScript code with full type definitions.
```

### Stream 1B: Web Frontend — Panchang & Calendar (Web Team, Dev 1)

**Complexity:** High | **Dependencies:** Stream 1A (API availability)

**Tasks:**
- [ ] Next.js project setup with Tailwind and design system
- [ ] Daily Panchang view (SSR for SEO)
- [ ] Time format toggle (12h/24h/24+)
- [ ] Month calendar view (grid with Hindu dates, festivals, moon phases)
- [ ] Day detail view
- [ ] Week view
- [ ] Year overview
- [ ] Location selector (auto-detect + manual search)
- [ ] Calendar preference settings
- [ ] Panchang element explanations (tap/click)
- [ ] Basic responsive/mobile layout

#### Claude Prompt — Web Frontend Core

```
Build the web frontend for "The Pandit" Hindu Panchang app using 
Next.js 14+ (App Router), TypeScript, and Tailwind CSS.

DESIGN SYSTEM:
- Consumer theme: saffron (#FF9933), gold (#FFD700), maroon (#800000), 
  cream (#FFF8DC), deep brown (#3E2723)
- Dark mode: dark backgrounds with warm accent colors
- Typography: clean, large Panchang values, readable for older users
- Mobile-first responsive design
- 8px spacing grid

PROJECT STRUCTURE:
```
src/
├── app/
│   ├── layout.tsx          # Root layout with nav, theme
│   ├── page.tsx            # Home → redirects to /today
│   ├── today/
│   │   └── page.tsx        # Daily Panchang (SSR)
│   ├── calendar/
│   │   ├── page.tsx        # Month view (default)
│   │   ├── week/page.tsx   # Week view
│   │   ├── year/page.tsx   # Year overview
│   │   └── [date]/page.tsx # Day detail
│   ├── festivals/
│   │   ├── page.tsx        # Festival list
│   │   └── [id]/page.tsx   # Festival detail (SSR for SEO)
│   └── settings/
│       └── page.tsx        # Location, calendar prefs
├── components/
│   ├── panchang/
│   │   ├── DailyPanchang.tsx    # Full daily view
│   │   ├── PanchangElement.tsx  # Single element with explanation
│   │   ├── TimeFormatToggle.tsx # 12h/24h/24+
│   │   ├── TodayHighlights.tsx  # Summary card
│   │   └── GoodAvoidIndicator.tsx
│   ├── calendar/
│   │   ├── MonthGrid.tsx        # Month calendar grid
│   │   ├── WeekStrip.tsx        # Week view
│   │   ├── YearOverview.tsx     # Year grid
│   │   ├── DayCell.tsx          # Single day in grid
│   │   └── CalendarNav.tsx      # Navigation controls
│   ├── festivals/
│   │   ├── FestivalCard.tsx     # Card in list
│   │   └── FestivalDetail.tsx   # Full detail page
│   ├── shared/
│   │   ├── LocationSelector.tsx # Auto-detect + search
│   │   ├── MoonPhaseIcon.tsx    
│   │   ├── TithiIcon.tsx        
│   │   └── Header.tsx           
│   └── ui/                      # Design system primitives
├── lib/
│   ├── api.ts           # API client (fetch wrapper)
│   ├── types.ts         # TypeScript types matching API
│   ├── cache.ts         # Client-side SWR/React Query config
│   └── formatters.ts   # Date, time, Panchang value formatters
└── styles/
    └── globals.css      # Tailwind config + custom theme
```

DAILY PANCHANG PAGE (SSR):
- Server-side renders today's Panchang for the user's location
- Location auto-detected from IP on first visit; saved preference after
- Shows: location, Gregorian date, Hindu date (Tithi, Paksha, Month)
- Summary card: today's highlights, festival/vrat if any, Rahu Kalam
- Detailed list: all Panchang elements with start/end times
- Each element tappable for explanation (modal/drawer)
- Time toggle: 12h / 24h / 24+ (sunrise-relative past-midnight)
- Navigation: previous/next day, jump to today, jump to date
- Actions: add note, add reminder, bookmark, share

MONTH CALENDAR VIEW:
- Grid layout (7 columns × 4-6 rows)
- Each cell shows: Gregorian date, Hindu date (tithi number), 
  moon phase icon, festival marker (colored dot), note indicator
- Header: month/year selector, region/calendar-type selector
- Festival color coding by category
- Today highlighted
- Tapping a day navigates to day detail view
- Lazy load: prefetch adjacent months

RESPONSIVE:
- Mobile: single column, card-based layout
- Tablet: 2-column where appropriate
- Desktop: full calendar grid with side panel for details

Use React Query (TanStack Query) for data fetching and caching.
Use framer-motion for smooth transitions.
Implement service worker for offline caching of current month data.

Output complete, production-ready Next.js code.
```

### Stream 1C: Web Frontend — User Features (Web Team, Dev 2)

**Complexity:** Medium | **Dependencies:** Stream 1A (API)

**Tasks:**
- [ ] Registration and login (Google, Apple, email)
- [ ] User profile and settings
- [ ] Notes CRUD (add to any date)
- [ ] Bookmarks CRUD with categories
- [ ] Reminders CRUD (basic Gregorian for MVP)
- [ ] Basic subscription management UI
- [ ] Share functionality (WhatsApp, email, copy link)

#### Claude Prompt — User Features Frontend

```
Build the user-facing features for "The Pandit" web app (Next.js 14+, 
TypeScript, Tailwind CSS). These integrate with the existing app layout 
and API.

FEATURES TO BUILD:

1. AUTHENTICATION:
   - /auth/login page with: Google OAuth, Apple Sign-In, Email/Password
   - /auth/register with same options + display name
   - Guest mode: banner "Create account to save your data"
   - Auth context provider with JWT token management
   - Protected route wrapper for Silver/Gold features

2. NOTES:
   - "Add Note" modal accessible from any calendar day
   - Note editor: title, body (rich text), category selector 
     (personal, puja, family, travel, temple, fasting, custom)
   - Notes list view: filterable by category, searchable
   - Note indicators on calendar days
   - Free tier: max 5 notes, show upgrade prompt

3. BOOKMARKS:
   - "Bookmark" button on any date, festival, or muhurat
   - Category: festival, family, muhurat, vrat, travel, temple, 
     personal, custom
   - Bookmarks page: list with filters, calendar overlay option
   - Free tier: max 5 bookmarks

4. REMINDERS:
   - "Add Reminder" from any date
   - Form: title, date/time, offset (at time, 5m/15m/30m/1h/1d/3d/1w before)
   - Reminders list: upcoming, past, active/inactive toggle
   - Push notification permission request flow
   - Free tier: max 5 reminders

5. PROFILE & SETTINGS:
   - Display name, email, avatar
   - Location management (primary + saved locations)
   - Calendar preferences (Amanta/Purnimanta, Samvat, regional style)
   - Language preference
   - Notification preferences (categories, quiet hours)
   - Subscription tier display + upgrade CTA

6. SUBSCRIPTION:
   - Pricing page showing Basic/Silver/Gold with feature comparison table
   - Stripe checkout integration for web
   - Current plan display, manage/cancel

7. SHARE:
   - Share button on daily Panchang, festivals, muhurat results
   - Generates a shareable card image (using html-to-image or canvas)
   - Share targets: copy link, WhatsApp, email, download image

Use React Hook Form for all forms, Zod for validation.
Implement optimistic updates for notes/bookmarks/reminders.
```

### Stream 1D: CMS & Content Population (Content Team)

**Complexity:** Medium | **Dependencies:** Stream 0C (schema)

**Tasks:**
- [ ] Build basic admin console (React) for content management
- [ ] Populate festival database (50+ major festivals with rules)
- [ ] Write festival content (descriptions, puja methods, significance)
- [ ] Create educational content (Panchang explainers)
- [ ] English and Hindi content for MVP
- [ ] Create festival rule definitions for the rule engine

#### Claude Prompt — Admin Console & CMS

```
Build the admin console for "The Pandit" using React, TypeScript, and 
Tailwind CSS. This is an internal tool for content management.

DESIGN: Use the Aqualeo design system — dark canvas background (#1a1a2e), 
single aqua accent (#00d4ff), mixed-case headlines, 8px spacing grid.

FEATURES:

1. FESTIVAL MANAGEMENT:
   - List all festivals with search, filter by region/deity
   - Create/edit festival rule:
     * Name, identifier
     * Anga rule builder (visual): select tithi, nakshatra, paksha, 
       month, scheme — with preview of resolved dates
     * Region tags (multi-select: North India, South India, Gujarat, 
       Maharashtra, Bengal, Tamil Nadu, etc.)
     * Deity, priority
   - Festival content editor per locale:
     * Rich text editor for description, significance, puja method, 
       katha, mantras
     * Samagri list builder (items with quantities)
     * Regional variations editor
     * Image upload
     * Review state workflow: Draft → In Review → Published
     * Version history with diff view

2. CONTENT MANAGEMENT:
   - Educational articles (Panchang basics, Tithi explanation, etc.)
   - Same review workflow as festivals
   - Regional relevance tagging
   - Source attribution field

3. REPORTING DASHBOARD:
   - User metrics: signups, DAU/MAU (placeholder charts)
   - Content metrics: most viewed festivals, content coverage
   - System metrics: cache hit rate, API latency

4. ACCESS CONTROL:
   - Login with admin credentials
   - Role display (Content, Ops, Finance, Superuser)
   - Audit log viewer

Use React Query for data fetching. Include a sidebar navigation.
Output as a standalone React app (Vite) that connects to the same 
backend API.
```

---

## 5. Phase 2: Enhanced Features (Web)

**Duration:** 6-8 weeks
**Goal:** Silver tier features — Tithi-based reminders, vrat tracker, festival prep, muhurat finder, family features, calendar export, HD calendar generator
**Parallel Streams:** 3

### Stream 2A: Tithi Reminders & Vrat Tracker (Backend + Frontend)

**Complexity:** High | **Dependencies:** Phase 1 complete

**Tasks:**
- [ ] Implement Tithi/Nakshatra-based recurrence engine
- [ ] Implement kshaya/vriddhi tithi resolution rules
- [ ] Implement location-change re-resolution
- [ ] Vrat tracker backend (CRUD + status tracking)
- [ ] Vrat tracker frontend (plan/observe/miss/complete flow)
- [ ] Recurring reminder UI (pick Tithi, Nakshatra, or festival cycle)
- [ ] Festival preparation mode (countdown timelines)

#### Claude Prompt — Tithi Recurrence Engine

```
Implement the Tithi-based recurrence engine for "The Pandit" reminder 
system. This is the CORE DIFFERENTIATOR — Hindu events recur by lunar 
calendar, not Gregorian dates.

REQUIREMENTS:
A reminder can recur by:
1. Gregorian date (standard: "every Jan 1")
2. Hindu Tithi ("every Kartik Purnima", "every Shukla Ekadashi")
3. Nakshatra ("every Rohini Nakshatra day")
4. Festival cycle ("every Diwali", "every Navratri start")
5. Monthly vrat cycle ("every Ekadashi", "every Pradosham")

RECURRENCE RESOLUTION LOGIC:
```typescript
interface RecurrenceSpec {
  type: 'gregorian' | 'tithi' | 'nakshatra' | 'festival' | 'monthly_vrat';
  // For tithi:
  tithi?: number;       // 1-30
  paksha?: 'shukla' | 'krishna';
  lunar_month?: string; // 'kartik', 'chaitra', etc. (null = every month)
  scheme?: 'amanta' | 'purnimanta';
  // For nakshatra:
  nakshatra?: number;   // 1-27
  // For festival:
  festival_rule_id?: string;
  // Regional convention for edge cases:
  regional_convention?: 'north' | 'south' | 'gujarat';
}
```

RESOLUTION ALGORITHM:
1. Read the Panchang cache for each day in the resolution horizon (≥15 months)
2. For each day, check if the recurrence rule matches:
   - Tithi: the specified tithi must be active at sunrise on that day
   - Match against paksha and lunar month if specified
3. KSHAYA TITHI HANDLING:
   - If the target tithi never spans a sunrise in a cycle (kshaya):
   - Use the day where the tithi is current at the conventional 
     reference moment per the regional convention on the rule
   - Log this as a kshaya-resolution for transparency
4. VRIDDHI TITHI HANDLING:
   - If the target tithi spans two sunrises (vriddhi):
   - Fire ONCE on the day chosen by regional convention
   - MUST NOT double-fire
5. Store resolved fire-times in the reminders table
6. On user location change: re-resolve ALL future fire-times
7. Resolution runs as a background job, not blocking the API

IMPLEMENTATION:
- TypeScript service in the backend
- Background worker that resolves reminders on a schedule
- Re-resolution triggered by: new reminder, location change, 
  panchang cache update
- Unit tests covering: normal tithi, kshaya, vriddhi, month-scheme 
  shift, location change

Also implement the Vrat Tracker:
- CRUD for vrat records (planned/observed/missed/completed)
- Pre-populated vrat types: Ekadashi, Pradosham, Sankashti, Purnima, 
  Amavasya, Shravan Somvar, Karva Chauth, etc.
- Integration with reminders: "Track this vrat" auto-creates a 
  recurring Tithi-based reminder
- Completion tracking with sankalp notes
```

### Stream 2B: Muhurat Finder & Calendar Generator (Backend + Frontend)

**Complexity:** High | **Dependencies:** Phase 1 complete

**Tasks:**
- [ ] Muhurat scoring engine (date range scan, avoidance windows, event rules)
- [ ] Muhurat finder API and UI
- [ ] HD calendar PDF generator (queue-driven, 300 DPI)
- [ ] Calendar template system
- [ ] Calendar generation UI (template picker, options, preview)
- [ ] Google/Apple calendar export (iCal format)

#### Claude Prompt — Muhurat Finder Engine

```
Build the Muhurat Finder engine for "The Pandit". This scans a date range, 
scores candidate windows against event-type rules, and returns 
best/good/avoid dates with explanations.

INPUT:
- Event type (wedding, griha_pravesh, namakaran, vehicle_purchase, 
  business_launch, travel, etc.)
- Date range (from, to)
- Location (lat, lon, tz)
- Preferences (avoid_rahu_kalam: true, preferred_weekday: [], 
  preferred_nakshatra: [], preferred_tithi: [])

SCORING LOGIC:
For each day in the range, read panchang cache and compute:

1. BASE SCORE (0-100):
   - Tithi suitability for event type (lookup table per event)
   - Nakshatra suitability (each nakshatra rated for each event type)
   - Yoga suitability
   - Weekday suitability

2. PENALTIES (deductions):
   - Rahu Kalam overlaps with ceremony time: -30
   - Yamaganda overlap: -20
   - Gulika overlap: -15
   - Krishna Paksha (for auspicious events): -10
   - Adhika maas (generally avoided for samskaras): -25
   - Specific avoided tithis (Rikta tithis for weddings): -20

3. BONUSES:
   - Abhijit Muhurat available: +10
   - Shubh yoga: +10
   - User's preferred weekday: +5
   - User's preferred nakshatra: +10

4. CLASSIFICATION:
   - Score ≥ 80: BEST (green)
   - Score 60-79: GOOD (yellow)
   - Score < 60: AVOID (red)

5. EXPLANATION:
   For each result, generate a human-readable explanation:
   "This date is excellent for Griha Pravesh. Pushya Nakshatra is 
   highly auspicious for entering a new home. Shukla Paksha. 
   Abhijit Muhurat available at 11:45 AM - 12:30 PM. 
   Note: Rahu Kalam is from 3:00 PM - 4:30 PM — schedule the 
   ceremony before that."

RESPONSE:
```json
{
  "results": [
    {
      "date": "2026-08-15",
      "score": 92,
      "classification": "best",
      "tithi": "Shukla Saptami",
      "nakshatra": "Pushya",
      "abhijit_muhurat": {"start": "11:45", "end": "12:30"},
      "rahu_kalam": {"start": "15:00", "end": "16:30"},
      "explanation": "Excellent for Griha Pravesh...",
      "warnings": ["Rahu Kalam in afternoon — schedule ceremony in morning"]
    }
  ],
  "summary": "Found 3 excellent dates and 5 good dates in your range."
}
```

Implement as a TypeScript service. Include the scoring lookup tables 
for at least these event types: wedding, griha_pravesh, namakaran, 
annaprashan, mundan, vehicle_purchase, business_launch, travel.

Also build the frontend: a form with event type, date range, location, 
preferences → results displayed as a scored list with color coding, 
expandable explanations, and "Save to Calendar" / "Set Reminder" / 
"Book a Pandit" actions.
```

### Stream 2C: Family Features & Widgets (Backend + Frontend)

**Complexity:** Medium | **Dependencies:** Phase 1 complete

**Tasks:**
- [ ] Family member management (CRUD with sensitive data vault)
- [ ] Hindu birthday tracking (Tithi/Nakshatra-based)
- [ ] Family ritual reminders (shraddha, annual pujas)
- [ ] Family calendar sharing UI
- [ ] Web dashboard widget layout
- [ ] Calendar sync (Google Calendar, Apple Calendar via iCal)

#### Claude Prompt — Family Features

```
Build the Family Features module for "The Pandit" web app.

BACKEND (TypeScript):
1. Family Members API:
   - POST /api/v1/family — add member (name, relation, birth details)
   - Birth date/time stored in SensitiveVault (encrypted)
   - Birth Tithi and Nakshatra stored in family_members table
   - Limit: Silver=5 members, Gold=unlimited
   
2. Hindu Birthday Resolution:
   - Given a birth Tithi (e.g., Kartik Shukla 5) and Nakshatra (Rohini)
   - Resolve the next occurrence using the Panchang cache
   - Create automatic reminders for Hindu birthdays
   - Support multiple birthday types: Gregorian, Tithi-based, Nakshatra-based

3. Family Ritual Reminders:
   - Shraddha dates (based on tithi of death — annual)
   - Annual puja dates (kuldevata puja, family traditions)
   - Marriage anniversary (both Gregorian and Hindu date)
   
4. Family Calendar Sharing:
   - Generate a shared family calendar view
   - Family invitation flow (email invite → accept)
   - Roles: admin (creator) and member
   - Shared events visible to all family members

FRONTEND (Next.js):
- Family settings page: list members, add/edit/remove
- Family calendar view: overlay all family events on the calendar
- Hindu birthday cards with next occurrence date
- Shraddha reminder setup wizard
```

---

## 6. Phase 3: Premium & AI Features (Web)

**Duration:** 6-8 weeks
**Goal:** Gold tier features — AI assistant, spiritual planner, advanced search, premium calendar features
**Parallel Streams:** 3

### Stream 3A: AI Assistant — Ask The Pandit (Backend + Frontend)

**Complexity:** High | **Dependencies:** Phase 1 CMS content populated

**Tasks:**
- [ ] Set up vector store (Pinecone/Weaviate) and index CMS corpus
- [ ] Build RAG pipeline (retrieval + Panchang context injection)
- [ ] Implement AI safety guardrails (grounding, disclaimer, sensitivity)
- [ ] Build chat UI (Ask The Pandit)
- [ ] Integrate with daily Panchang and festival pages

#### Claude Prompt — AI Assistant RAG Service

```
Build the "Ask The Pandit" AI assistant for the Hindu Panchang app.
This is a RAG (Retrieval-Augmented Generation) service.

ARCHITECTURE:
1. Vector Store: Pinecone (or Weaviate) indexed with:
   - All published festival content (descriptions, puja methods, katha)
   - Educational content (Panchang explanations)
   - Vrat rules and procedures
   - Mantra references
   Index by: content chunks (~500 tokens each) with metadata 
   (festival_id, locale, content_type, region_tags)

2. Context Builder:
   - User query → retrieve top 5 relevant chunks from vector store
   - Inject today's Panchang data (from cache) as structured context
   - Inject user's location and calendar preferences

3. LLM Service:
   - System prompt enforcing:
     a) Only answer from retrieved context + Panchang data
     b) Never invent ritual instructions
     c) Always append: "Please consult a qualified pandit or family 
        elders for important ceremonies."
     d) Present regional variations neutrally
     e) Never assert one tradition as the only correct one
   - Use OpenAI GPT-4 or Claude API
   - Stream responses for better UX

4. Safety:
   - Input: filter harmful/irrelevant queries
   - Output: check for unsupported claims, add disclaimers
   - Logging: store all queries and responses for quality review
   - Rate limit: Silver=10/day, Gold=50/day

IMPLEMENTATION (TypeScript + Python):
- Python service for embeddings + vector search
- TypeScript API endpoint: POST /api/v1/ai/ask
- Request: { query: string, context?: { date?, location?, festival_id? } }
- Response: streaming text with source citations

FRONTEND:
- Chat-like interface accessible from main nav ("Ask The Pandit")
- Also embedded as a contextual helper on:
  - Daily Panchang page ("Ask about today's Panchang")
  - Festival pages ("Ask about this festival")
  - Muhurat results ("Explain this recommendation")
- Conversation history (last 10 exchanges per session)
- Suggested questions based on today's date and upcoming festivals
```

### Stream 3B: Hindu Life Planner & Spiritual Features (Backend + Frontend)

**Complexity:** Medium | **Dependencies:** Phase 2 complete

**Tasks:**
- [ ] Daily spiritual planner (today's suggestions based on Panchang)
- [ ] Monthly spiritual planner (upcoming opportunities)
- [ ] Annual Hindu planner
- [ ] Sankalp journal (spiritual diary)
- [ ] Mantra & japa tracker
- [ ] Daily dharma card (shareable)
- [ ] Children's learning mode (simplified festival stories)

#### Claude Prompt — Spiritual Planner

```
Build the Hindu Life Planner module for "The Pandit" (Gold tier feature).

THREE PLANNER HORIZONS:

1. DAILY SPIRITUAL PLANNER (GET /api/v1/planner/daily):
   Based on today's Panchang, generate personalized suggestions:
   - Today's recommended deity for worship (based on weekday + tithi)
   - Suggested mantra (weekday-based + nakshatra-based)
   - Best time for japa/meditation (based on Brahma Muhurat, Abhijit)
   - Recommended dana/charity (weekday-based tradition)
   - Vrat reminder if applicable (Ekadashi, Pradosham, etc.)
   - Rahu Kalam caution with times
   - Sandhya Vandanam reminder (sunrise/sunset based)
   - Simple puja suggestion

2. MONTHLY PLANNER (GET /api/v1/planner/monthly):
   - Upcoming festivals with prep timelines
   - Good puja days, charity days
   - Recommended temple visit days
   - Vrat schedule for the month
   - Monthly sankalp (goal setting)

3. ANNUAL PLANNER (GET /api/v1/planner/annual):
   - All festivals mapped to the year
   - Family samskaras due (based on family member ages)
   - Shraddha dates
   - Pilgrimage suggestions (seasonal)
   - Chaturmas period
   - Annual spiritual goals

SANKALP JOURNAL:
- CRUD for journal entries
- Types: daily sankalp, vrat notes, puja experience, mantra count,
  gratitude, temple visit, spiritual goals, charity record
- Calendar integration: journal entries appear on calendar days
- Streak tracking for daily practice

DAILY DHARMA CARD:
- Auto-generated shareable card with:
  Today's Tithi, suggested deity, mantra, good action, festival/vrat
- Render as image (server-side using sharp/canvas)
- Share to WhatsApp, Instagram Stories, download
```

### Stream 3C: Advanced Search & Premium Calendars (Backend + Frontend)

**Complexity:** Medium | **Dependencies:** Phase 1-2 complete

**Tasks:**
- [ ] Advanced search engine (natural language queries)
- [ ] Premium calendar templates (5+ designs)
- [ ] 12-15 month HD calendar generator improvements
- [ ] Commercial/business calendar branding
- [ ] Temple/community calendar builder

---

## 7. Phase 4: Marketplaces (Web)

**Duration:** 10-12 weeks
**Goal:** Launch Pandit services marketplace (in-person first) and Pooja items marketplace
**Parallel Streams:** 2 (fully independent marketplaces)

### Stream 4A: Pandit Services Marketplace

**Complexity:** Very High | **Dependencies:** Phase 1-2 complete

**Sub-phases:**
1. **4A.1 — Provider Onboarding (2-3 weeks)**
   - Pandit registration flow
   - KYC integration (Stripe Identity)
   - Service catalogue builder
   - Availability management
   - Stripe Connect payout onboarding
   - Admin approval queue

2. **4A.2 — Booking Engine (3-4 weeks)**
   - Discovery/search with filters
   - Booking flow with muhurat integration
   - Slot reservation (atomic)
   - Pricing/quote calculator
   - Stripe escrow payment
   - Booking lifecycle state machine
   - Cancellation/refund policy engine

3. **4A.3 — Communication & Trust (2-3 weeks)**
   - In-app messaging (WebSocket)
   - PII masking
   - Two-way reviews (verified-booking only)
   - Ranking/recommendation algorithm
   - Dispute resolution workflow
   - Provider standing system

4. **4A.4 — Admin & Payouts (1-2 weeks)**
   - Marketplace admin panel
   - Payout processing and reconciliation
   - Dispute console
   - Reporting dashboard

#### Claude Prompt — Pandit Marketplace Booking Engine

```
Build the booking engine for "The Pandit" Pandit Services Marketplace.
This is the core component of a two-sided service marketplace.

BOOKING STATE MACHINE:
States: REQUESTED → CONFIRMED → IN_PROGRESS → COMPLETED
        REQUESTED → DECLINED (by pandit or timeout)
        CONFIRMED → RESCHEDULED → CONFIRMED
        CONFIRMED → CANCELLED_PATRON | CANCELLED_PANDIT
        COMPLETED → REVIEWED
        Any → DISPUTED → RESOLVED

IMPLEMENTATION:

1. BOOKING CREATION (POST /api/v1/marketplace/bookings):
   Input: {
     pandit_id, pandit_service_id, mode ('in_person'|'remote'),
     date, start_time, timezone,
     address_id? (for in-person),
     samagri_option: 'pandit_brings' | 'self_arrange',
     notes, muhurat_ref?
   }
   
   Steps:
   a) Validate pandit exists and is approved+verified
   b) Validate service exists for this pandit
   c) Validate date is within 60-day advance window and ≥ lead time
   d) CHECK AVAILABILITY: atomic slot reservation
      - Read pandit's availability rules
      - Check no conflicting confirmed booking
      - Reserve slot with 5-minute payment TTL
      - Use Redis lock: `booking_lock:{pandit_id}:{date}:{slot}`
   e) COMPUTE PRICE:
      - Base fee (from PanditService)
      - Travel fee (if in-person, compute distance from pandit base)
      - Samagri charge (if pandit_brings)
      - Platform service fee (configurable %)
      - Tax (per patron jurisdiction)
      - Return itemized quote
   f) CAPTURE PAYMENT:
      - Create Stripe PaymentIntent with transfer_data for marketplace
      - If pandit acceptance mode = 'auto': capture immediately
      - If 'manual': authorize only, capture on pandit acceptance
   g) Create Booking record with policy_snapshot (current cancellation tiers)
   h) Emit event: booking.requested or booking.confirmed
   i) Release slot lock on failure; extend to confirmed on success

2. PANDIT ACCEPTANCE (PATCH /api/v1/provider/bookings/:id/accept):
   - Validate pandit owns this booking
   - Validate within response window
   - Capture the authorized payment
   - Transition: REQUESTED → CONFIRMED
   - Emit: booking.confirmed → triggers patron notification + reminder

3. COMPLETION (PATCH /api/v1/marketplace/bookings/:id/complete):
   - Either party confirms completion
   - Start holdback timer (configurable, default 48h)
   - After holdback: compute payout (total - commission - fees)
   - Create Stripe Transfer to pandit's connected account
   - Emit: booking.completed → triggers review request

4. CANCELLATION (PATCH /api/v1/marketplace/bookings/:id/cancel):
   - Read policy_snapshot from booking
   - Compute refund based on time-to-ceremony:
     * 30+ days: full refund (less non-refundable platform fee)
     * 7-30 days: 50% refund
     * <7 days or no-show: no refund
   - Process Stripe refund
   - If pandit cancelled: always full refund + pandit penalty
   - Emit: booking.cancelled

5. AVAILABILITY SERVICE:
   - Check rules: working hours, days off, blackout, lead time, buffer
   - Atomic slot check: 
     SELECT ... WHERE pandit_id = ? AND date = ? AND time_overlaps(?)
     FOR UPDATE SKIP LOCKED
   - Return available slots for a given pandit + date range

Include comprehensive TypeScript types, error handling, and unit tests
for the state machine transitions and edge cases (double-booking attempt,
expired slot lock, payment failure mid-booking, pandit timeout).
```

### Stream 4B: Pooja Items Marketplace

**Complexity:** High | **Dependencies:** Phase 1-2 complete

**Sub-phases:**
1. **4B.1 — Shopify Integration (2-3 weeks)**
   - Headless Shopify store setup
   - Storefront API integration (catalogue, cart)
   - Shopify checkout embedding
   - Webhook processing pipeline

2. **4B.2 — Seller Portal (2-3 weeks)**
   - Seller onboarding and KYC
   - Product listing (weight/count/bundle variants)
   - Order management and dispatch tracking
   - Fulfillment write-back to Shopify
   - Seller dashboard

3. **4B.3 — Buyer Experience (2-3 weeks)**
   - Product browsing and search
   - Festival/checklist bundle integration
   - Multi-seller cart and checkout
   - Order tracking
   - Returns and reviews

4. **4B.4 — Commission & Payouts (1-2 weeks)**
   - Shopify webhook → commission calculation
   - Payout via shared Stripe Connect engine
   - Reconciliation and reporting
   - Admin controls

#### Claude Prompt — Shopify Integration

```
Build the headless Shopify integration for "The Pandit" Pooja Items 
Marketplace. The platform uses one Shopify store as the commerce backbone; 
sellers never access Shopify directly.

ARCHITECTURE:
- Shopify Storefront API (GraphQL): catalogue browsing, cart, checkout
- Shopify Admin API: product creation/update (via seller portal), 
  fulfillment write-back, inventory, refunds
- Shopify Webhooks: order events, fulfillment, refunds → platform processing

IMPLEMENTATION (TypeScript):

1. SHOPIFY CLIENT (src/services/shopify/):
   ```
   shopify-storefront.ts  — Storefront API client (public, buyer-facing)
   shopify-admin.ts       — Admin API client (server-only, seller ops)
   shopify-webhooks.ts    — Webhook handler + verification
   ```

2. PRODUCT MANAGEMENT (Seller Portal → Shopify):
   When a seller creates/updates a product in The Pandit seller portal:
   a) Validate the product data (title, images, variants, price, stock)
   b) Create/update the product in Shopify via Admin API
   c) Set vendor = seller_id (Shopify vendor field)
   d) Set metafields: seller_id, category, festival_ref, checklist_ref,
      product_type (weight/count/bundle)
   e) Store ProductRef in platform DB (maps shopify_product_id to seller)
   
   Variant patterns:
   - By weight: option "Weight" with values "100g", "250g", "500g", "1kg"
   - By count: option "Pack Size" with values "5", "11", "21", "51"
   - Bundle: Shopify bundle product with component references

3. BUYER CATALOGUE (Storefront API):
   GraphQL queries for:
   - Product listing with filters (category, price, festival)
   - Product detail with variants
   - Cart operations (create, add, update, remove)
   - Checkout URL generation
   
   Subscription gate: before generating checkout URL, verify buyer has 
   active Silver/Gold subscription (server-side check, not client)

4. WEBHOOK PROCESSING:
   Endpoint: POST /api/v1/webhooks/shopify
   
   Handle these events:
   - orders/paid → create OrderRef + OrderSellerSplit records;
     emit order.paid event; notify seller
   - orders/fulfilled → update status; emit order.fulfilled;
     schedule seller payout (after holdback)
   - refunds/create → update OrderRef; reverse/adjust payout;
     notify buyer and seller
   
   Processing rules:
   - Verify HMAC signature on every webhook
   - Idempotency: check webhook ID hasn't been processed
   - Dead-letter queue for failed processing
   - Reconciliation cron: every hour, check for missed webhooks 
     by comparing Shopify orders (last 24h) vs platform OrderRefs

5. FULFILLMENT WRITE-BACK:
   When seller marks order dispatched in portal:
   a) Seller enters carrier + tracking number
   b) Platform calls Shopify Admin API: POST fulfillment
   c) Shopify sends tracking notification to buyer
   d) Update OrderRef status to 'shipped'

6. PAYOUT INTEGRATION:
   After delivery + holdback:
   - Compute: item_subtotal × (1 - commission_rate) = seller_payout
   - Shipping passes through to seller
   - Use shared Payout Engine (Stripe Connect)

Include error handling, retry logic, and monitoring for webhook gaps.
```

---

## 8. Phase 5: Mobile Apps

**Duration:** 8-10 weeks
**Goal:** Native iOS and Android apps with all features from web, plus widgets and lock-screen
**Parallel Streams:** 2 (iOS and Android developed simultaneously)

### Stream 5A: iOS App (Swift/SwiftUI)

**Complexity:** High | **Dependencies:** All backend APIs stable

**Tasks:**
- [ ] Project setup with SwiftUI
- [ ] API client and authentication
- [ ] Daily Panchang view
- [ ] Calendar views (day, week, month, year)
- [ ] Festival pages
- [ ] Notes, bookmarks, reminders
- [ ] Subscription management (Apple IAP)
- [ ] Push notifications (APNs)
- [ ] Home screen widgets (WidgetKit)
- [ ] Lock-screen widgets
- [ ] Offline caching (CoreData/SwiftData)
- [ ] Pandit marketplace (booking, messaging)
- [ ] Pooja items (Shopify mobile SDK)
- [ ] Share extensions

#### Claude Prompt — iOS App

```
Build the iOS app for "The Pandit" Hindu Panchang app using 
Swift and SwiftUI (iOS 17+).

ARCHITECTURE: MVVM with a shared API service layer.

PROJECT STRUCTURE:
```
ThePandit/
├── App/
│   ├── ThePanditApp.swift
│   ├── AppState.swift         # Global state
│   └── ContentView.swift      # Tab navigation
├── Core/
│   ├── API/
│   │   ├── APIClient.swift    # URLSession-based, async/await
│   │   ├── AuthService.swift  # OAuth (Google/Apple) + JWT
│   │   └── Endpoints.swift    # All API endpoints
│   ├── Cache/
│   │   ├── PanchangCache.swift # SwiftData for offline
│   │   └── SyncManager.swift   # Background sync
│   ├── Models/                 # Codable data models
│   └── Auth/
│       ├── GoogleAuth.swift
│       └── AppleAuth.swift
├── Features/
│   ├── Panchang/
│   │   ├── DailyPanchangView.swift
│   │   ├── PanchangViewModel.swift
│   │   └── Components/
│   ├── Calendar/
│   │   ├── MonthCalendarView.swift
│   │   ├── WeekView.swift
│   │   ├── DayDetailView.swift
│   │   └── CalendarViewModel.swift
│   ├── Festivals/
│   │   ├── FestivalListView.swift
│   │   └── FestivalDetailView.swift
│   ├── Notes/
│   ├── Reminders/
│   ├── Marketplace/
│   │   ├── PanditSearchView.swift
│   │   ├── BookingFlowView.swift
│   │   └── MessagingView.swift
│   ├── Shop/                    # Shopify Mobile Buy SDK
│   ├── Planner/
│   ├── Family/
│   ├── AI/
│   │   └── AskThePanditView.swift
│   └── Settings/
│       ├── ProfileView.swift
│       ├── SubscriptionView.swift # StoreKit 2
│       └── PreferencesView.swift
├── Widgets/
│   ├── TodayWidget.swift        # Tithi + Nakshatra
│   ├── FestivalCountdownWidget.swift
│   ├── RahuKalamWidget.swift
│   └── DailyMantraWidget.swift
├── Notifications/
│   └── PushHandler.swift
└── Resources/
    ├── Assets.xcassets
    └── Localizable.strings (en, hi)
```

KEY IMPLEMENTATION:
1. Tab bar: Today | Calendar | Festivals | Marketplace | Profile
2. Daily Panchang: pull-to-refresh, time toggle, element explanations
3. Widgets: WidgetKit with TimelineProvider, multiple widget families
4. Subscriptions: StoreKit 2 with server-side receipt verification
5. Push: UNUserNotificationCenter with custom categories
6. Offline: SwiftData for current month + recent days
7. Theme: warm devotional colors with dark mode support

Implement the Daily Panchang view and the Home Screen Widget as 
the starting point. Include the API client with auth.
```

### Stream 5B: Android App (Kotlin/Jetpack Compose)

**Complexity:** High | **Dependencies:** All backend APIs stable

**Tasks:** Mirror of iOS stream with Android-specific implementations:
- [ ] Project setup with Jetpack Compose
- [ ] API client and authentication
- [ ] All feature views (matching iOS)
- [ ] Subscription management (Google Play Billing)
- [ ] Push notifications (FCM)
- [ ] Home screen widgets (Glance API)
- [ ] Offline caching (Room)
- [ ] Shopify mobile SDK integration

#### Claude Prompt — Android App

```
Build the Android app for "The Pandit" Hindu Panchang app using 
Kotlin and Jetpack Compose (minimum SDK 26, target 35).

ARCHITECTURE: MVVM with Hilt dependency injection, Repository pattern.

Follow the same feature set as the iOS app but with Android-specific:
- Jetpack Compose for all UI
- Room for offline database
- WorkManager for background sync
- Glance API for home screen widgets
- Google Play Billing Library for subscriptions
- Firebase Cloud Messaging for push
- Credential Manager for Google Sign-In

PROJECT STRUCTURE:
```
app/src/main/java/com/thepandit/
├── di/                    # Hilt modules
├── data/
│   ├── api/               # Retrofit API client
│   ├── db/                # Room database
│   ├── repository/        # Repository implementations
│   └── models/            # Data classes
├── domain/
│   ├── models/            # Domain models
│   └── usecases/          # Use cases
├── ui/
│   ├── theme/             # Material3 theme (devotional colors)
│   ├── navigation/        # NavHost
│   ├── panchang/          # Daily Panchang screens
│   ├── calendar/          # Calendar views
│   ├── festivals/         # Festival screens
│   ├── marketplace/       # Pandit booking
│   ├── shop/              # Pooja items
│   ├── planner/           # Spiritual planner
│   ├── settings/          # Profile, subscription
│   └── components/        # Shared composables
├── widgets/               # Glance widgets
├── notifications/         # FCM handler
└── workers/               # WorkManager tasks
```

Implement the main navigation, Daily Panchang view, and a home 
screen widget as the starting point.
```

---

## 9. Parallel Development Matrix

This matrix shows which streams can run concurrently:

```
WEEK    1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30

PHASE 0:
  0A    ████████████                                    Infrastructure
  0B    ████████████████                                Panchang Engine
  0C    ████████████████                                Schema + Harness

PHASE 1:
  1A              ████████████████████████████          Backend APIs
  1B                    ████████████████████████████    Web: Panchang/Calendar
  1C                    ████████████████████████████    Web: User Features
  1D              ████████████████████████████          CMS + Content

PHASE 2:
  2A                                      ████████████████████          Tithi Reminders + Vrat
  2B                                      ████████████████████          Muhurat + Calendar PDF
  2C                                      ████████████████████          Family + Widgets

PHASE 3:
  3A                                                        ████████████████████    AI Assistant
  3B                                                        ████████████████████    Spiritual Planner
  3C                                                        ████████████████████    Search + Premium Cal

PHASE 4:
  4A                                                        ████████████████████████████████    Pandit Marketplace
  4B                                                        ████████████████████████████████    Pooja Marketplace

PHASE 5:
  5A                                                                          ████████████████████████    iOS
  5B                                                                          ████████████████████████    Android
```

**Key Parallelism Opportunities:**
1. **Phase 0:** All three streams are fully independent
2. **Phase 1:** 1A/1D can start in parallel; 1B/1C follow once API is available
3. **Phase 2:** All three streams are independent of each other
4. **Phase 3:** All three streams are independent; can overlap with Phase 4
5. **Phase 4:** Both marketplaces are fully independent of each other
6. **Phase 5:** iOS and Android are fully parallel

**Critical Path:** Phase 0B (Engine) → Phase 1A (Backend) → Phase 2A (Tithi Reminders) → Phase 4A (Pandit Marketplace)

---

## 10. Risk Register & Mitigation

| # | Risk | Probability | Impact | Mitigation |
|---|------|:-----------:|:------:|------------|
| 1 | **Swiss Ephemeris accuracy** doesn't match published Panchangs | Low | Critical | Validation harness in Phase 0; reference dataset; block on regression |
| 2 | **Swiss Ephemeris commercial licence** delayed | Medium | Critical | Start process in Phase 0; use AGPL for dev/staging; licence is launch gate |
| 3 | **Tithi edge cases** (kshaya/vriddhi) cause incorrect dates | Medium | High | Comprehensive test coverage; regional convention config; manual override path |
| 4 | **Shopify multivendor limitations** | Medium | Medium | Use vendor+metafield pattern; platform is merchant of record; have exit plan to Medusa.js |
| 5 | **Stripe Connect payout complexity** across jurisdictions | Medium | High | Start with US/UK only; add tax/compliance per region incrementally |
| 6 | **Marketplace cold-start** (no pandits/sellers) | High | High | Seed 20-30 pandits per launch city; personal onboarding; new-provider visibility boost |
| 7 | **Video SDK cost** at scale | Medium | Medium | Evaluate 3 providers; negotiate volume pricing; audio-only fallback |
| 8 | **Content sensitivity** (religious offense) | Low | High | Editorial review workflow; regional consultants; disclaimers; rapid takedown |
| 9 | **App Store rejection** over payment routing | Low | High | Clear separation: IAP for subs, Stripe for real-world services; document compliance |
| 10 | **Performance under festival spikes** | Medium | High | Cache pre-warming; auto-scaling; CDN; load testing before major festivals |

---

## 11. Launch Gates

### Pre-MVP Launch
- [ ] Swiss Ephemeris accuracy harness is green (100% pass)
- [ ] Daily Panchang loads in <2s for top 50 cities
- [ ] 50+ festivals with complete content (English + Hindi)
- [ ] User registration and subscription flow tested end-to-end
- [ ] Basic calendar views functional
- [ ] Push notifications working
- [ ] Privacy policy and terms published
- [ ] GDPR data export/deletion flows working

### Pre-Production Launch (with Marketplace)
- [ ] Swiss Ephemeris **commercial licence** secured
- [ ] Stripe Connect approved and configured for US/UK
- [ ] Shopify store configured and webhook pipeline tested
- [ ] KYC provider integrated and tested
- [ ] Cancellation/refund policy published
- [ ] Tax configuration for launch markets
- [ ] 20+ seed pandits onboarded per launch city
- [ ] 5+ seed sellers with products listed
- [ ] Load testing completed for festival-spike scenario
- [ ] Security audit completed
- [ ] App Store / Play Store submission requirements met

---

*End of Phased Development Plan v2.0*
