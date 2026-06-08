# The Pandit — Project Context

> This file is the single source of shared truth for the build.
> It is distilled from **Architecture Document v1.1** and **Development Plan v1.1** (Aqualeo).
> Do not contradict it.

---

## 1. What we are building

**The Pandit** is a location-accurate Hindu **Panchang**, calendar, planning and
spiritual-lifestyle platform delivered as:

- a **responsive web app**,
- **native iOS and Android apps**,
- an internal **admin console**, and
- a **modular backend** that does all the real work.

Product correctness depends almost entirely on one thing: an accurate,
location-aware Panchang engine. Every calendar cell, festival date, muhurat
window and Tithi-based reminder is downstream of that engine.

---

## 2. Architectural North Star (non-negotiable)

1. The **Panchang engine is the single source of astronomical truth.** Nothing
   recomputes it independently.
2. Panchang is **precomputed and cached, never calculated live on the device.**
3. Religious / festival content is **data, edited through a CMS, never hard-coded.**
4. Clients are **thin**; planning intelligence lives server-side and is shared
   across iOS, Android and web.

---

## 3. Build non-negotiables

1. Build and validate the **Panchang engine FIRST.** Everything downstream trusts it.
2. Use the **FREE Swiss Ephemeris (AGPL) build** for dev/test; the **commercial
   licence is a hard launch gate** (Stage 3 hardening). Production/public builds
   must not ship until it is secured.
3. **Never recompute Panchang on the client.** Clients read the API and cache results.
4. **Festivals are rules in a rule engine, never hard-coded dates.**
5. Treat **birth details and family data as sensitive from the first commit**
   (encrypted vault, access-logged, excluded from analytics).
6. **Every step ends with its checks green in CI** before the next begins.
7. Work the steps **top to bottom, in order.**

---

## 4. Committed technology stack

| Concern            | Choice                                                         |
|--------------------|----------------------------------------------------------------|
| Repo layout        | **Single monorepo** (`apps/*`, `services/*`, `packages/*`)    |
| Backend            | **Python 3.12 + FastAPI**, throughout all domain services      |
| Panchang engine    | **Swiss Ephemeris via `pyswisseph`** (AGPL build in dev)      |
| Methodology        | **Drik Ganita** (observational), modern ephemeris              |
| Web client         | **Next.js (App Router) + TypeScript + Tailwind**              |
| Admin console      | **React + TypeScript** (Next.js route group or Vite SPA)      |
| iOS app            | **Native Swift + SwiftUI**                                    |
| Android app        | **Native Kotlin + Jetpack Compose**                           |
| Primary DB         | **PostgreSQL**                                                |
| Cache / queue      | **Redis** + a managed job queue (RQ/Celery/Arq)               |
| Object storage     | **S3-compatible** (generated calendars, media)                |
| Push               | **APNs + FCM** via a fan-out service                          |
| Auth               | OAuth/OIDC (Google + Apple), email/phone, guest mode           |
| API surface        | One **versioned REST/JSON gateway** (GraphQL optional later)  |
| Container/dev      | Docker + docker-compose for local Postgres/Redis/MinIO         |

---

## 5. Engine parameters

| Parameter        | Decision                                               |
|------------------|--------------------------------------------------------|
| Ayanamsa         | **Lahiri (Chitrapaksha)** default; allow override      |
| Day boundary     | **Sunrise-to-sunrise**, per location                   |
| Month scheme     | Both **Amanta & Purnimanta**, user-selectable          |
| Leap month       | Detect & label **Adhika / Kshaya maas**                |
| Reference source | Validate against an established **published Panchang** |
| Time display     | **12h / 24h / 24-plus** (past-midnight) forms          |

---

## 6. Domain services

1. **Panchang Computation** — wraps Swiss Ephemeris; only writer of raw Panchang truth.
2. **Calendar Assembly** — composes day/week/month/year + 12–15-month views.
3. **Festival & Vrat Rules** — rule engine resolving festivals to dates per location/scheme.
4. **Reminders & Scheduling** — Gregorian + Tithi/Nakshatra recurrences → fire-times.
5. **Planner & Muhurat** — "find best date" engine (Phase 2+).
6. **Calendar PDF Generation** — async, queue-driven 300-DPI print PDFs.
7. **AI Assistant** — "Ask The Pandit", retrieval-grounded (Phase 3).
8. **Content / CMS** — editorial store + workflow for all non-astronomical content.
9. **Users & Profiles** — accounts, auth, prefs, locations, family, birth vault.
10. **Subscriptions & Billing** — Basic/Silver/Gold tiers, entitlement checks.

---

## 7. Global UI/UX Exclusion Policy

A separate design team owns the visual design (the Aqualeo design system).
**Claude Code must NOT invent, generate, or "polish" any UI/UX.**

### You MUST build (the functional layer)
- Navigation, routing, screen/component structure and composition.
- State management, data fetching, API integration.
- Business logic, form handling, validation, error/empty/loading states.
- A thin, swappable theming interface: design tokens referenced **by name**.

### You MUST NOT
- Invent colour values, gradients, fonts, type scales, shadows, icons, or animations.
- Author finished visual styling or make aesthetic/layout-design decisions.

All visual values must flow through named tokens from
`packages/design-tokens/tokens.placeholder.json`, marked `TODO(design)`.

---

## 8. Definition of Done — the whole build

- The accuracy harness is green and gating every merge.
- No client computes Panchang; all reads go through the cached API.
- Sensitive data is encrypted, access-logged and export/delete-able.
- The web experience is themeable via the Aqualeo design system.
- Each tier's entitlements are enforced at the gateway.
- The Swiss Ephemeris **commercial licence is secured before any public launch build**.
