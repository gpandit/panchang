# Build Status — Pandit Services Marketplace

Resumable progress manifest for the build defined in [`dev-plan-marketplace.md`](dev-plan-marketplace.md).
Architecture context: [`architecture-marketplace.md`](architecture-marketplace.md).

**How a runner uses this file:** pick the next step whose dependencies are all `done`, build it on
the assigned model, run its *Done when* checks, commit with the step ID, then flip its row to `done`
and fill the branch/commit. Statuses: `todo` · `in-progress` · `done` · `blocked`.

**Legend:** 🔴 = run on Opus · 🟢 = run on Sonnet · — = human/ops (not code-gen).

---

## WS-F · Foundation (serial — do first)

| Step | Model | Status | Branch / commit | Notes |
|---|---|---|---|---|
| F1 Persistence layer (Postgres + SQLAlchemy async + Alembic) | 🔴 Opus | done | fix/staging-deploy-workflow | async engine + `get_session` dep + `Repository` added atop existing sync/Alembic layer; psycopg3 async driver (no asyncpg), aiosqlite for tests |
| F2 Marketplace schema + no-double-booking constraint | 🔴 Opus | done | marketplace-build | 16 ORM models + Pydantic schemas; Alembic 0002 with PG `EXCLUDE USING gist` overlap constraint (`btree_gist`, active-status predicate) + `policy_snapshot` JSONB; sqlite/PG split so `create_all` works on aiosqlite; PG-gated overlap test (runs in CI). Local: 95 passed, 1 skipped |
| F3 Dual-role identity + Vault refs | 🔴 Opus | todo | | depends F1, F2 |
| F4 Module skeleton + router registration | 🟢 Sonnet | todo | | depends F1 |
| F5 Service taxonomy seed | 🟢 Sonnet | todo | | depends F2 |

## WS-A · Provider side (∥ WS-B after F)

| Step | Model | Status | Branch / commit | Notes |
|---|---|---|---|---|
| A1 Provider registration & onboarding | 🟢 Sonnet | todo | | depends F3, F4 |
| A2 Verification & KYC (Vault-backed) | 🔴 Opus | todo | | depends F3, A1, X1 |
| A3 Catalogue / modes / travel / samagri / pricing | 🟢 Sonnet | todo | | depends F5, A1 |
| A4 Availability & scheduling | 🔴 Opus | todo | | depends F2, A1 |
| A5 Provider dashboard | 🟢 Sonnet | todo | | depends A1,A3,A4,C1,C2,D1,D3 |

## WS-B · Patron side (∥ WS-A after F)

| Step | Model | Status | Branch / commit | Notes |
|---|---|---|---|---|
| B1 Discovery & search | 🟢 Sonnet | todo | | depends F2, F5 |
| B2 Pandit profile view | 🟢 Sonnet | todo | | depends F2, A3 |
| B3 Booking flow + Quote contract | 🔴 Opus | todo | | depends F2, B2, A3, A4 |
| B4 Manage / reschedule / cancel / recurring | 🟢 Sonnet | todo | | depends B3, C1, C4 |

## WS-C · Money & Lifecycle (after F2 + B3 quote contract)

| Step | Model | Status | Branch / commit | Notes |
|---|---|---|---|---|
| C1 Booking lifecycle state machine + audit | 🔴 Opus | todo | | depends F2, B3 |
| C2 Stripe Connect escrow / payouts / webhooks | 🔴 Opus | todo | | depends F2, B3, X1 |
| C3 Commission & fee engine | 🔴 Opus | todo | | depends B3, C2 |
| C4 Cancellation / refund / no-show engine | 🔴 Opus | todo | | depends B3, C1, C2 |
| C5 Tax & multi-currency | 🔴 Opus | todo | | depends B3, C2 |

## WS-D · Communication & Trust (∥ A/B/C)

| Step | Model | Status | Branch / commit | Notes |
|---|---|---|---|---|
| D1 In-app messaging (PII-masked) | 🟢 Sonnet | todo | | depends F2, B2, B3 |
| D2 Notifications (extends §11) | 🟢 Sonnet | todo | | depends F4 + event sources |
| D3 Reviews, ratings & ranking | 🔴 Opus | todo | | depends C1, B1 |
| D4 Trust, safety & disputes | 🔴 Opus | todo | | depends C1, C2, D1, D3 |
| D5 Live 1:1 video **[P2]** | 🟢 Sonnet | todo | | depends C1, B3, X1 |

## WS-E · Admin & Operations (∥ A/B/C/D)

| Step | Model | Status | Branch / commit | Notes |
|---|---|---|---|---|
| E1 Provider approval queue | 🟢 Sonnet | todo | | depends A1, A2 |
| E2 Service-taxonomy management | 🟢 Sonnet | todo | | depends F5 |
| E3 Commission & fee configuration | 🟢 Sonnet | todo | | depends C3, C4 |
| E4 Booking & dispute console | 🟢 Sonnet | todo | | depends C1, C4, D4 |
| E5 Payout management & reconciliation | 🟢 Sonnet | todo | | depends C2, C5 |
| E6 Content moderation + fraud dashboards | 🟢 Sonnet | todo | | depends D1, D3, D4 |

## WS-G · Clients (web leads; mobile ∥ once contract frozen)

| Step | Model | Status | Branch / commit | Notes |
|---|---|---|---|---|
| G-W1 Web: provider onboarding/verification/catalogue/availability | 🟢 Sonnet | todo | | A1–A4 |
| G-W2 Web: search + profile (SSR) | 🟢 Sonnet | todo | | B1, B2 |
| G-W3 Web: booking + quote + payment | 🟢 Sonnet | todo | | B3, C2, C5 |
| G-W4 Web: patron manage + provider dashboard | 🟢 Sonnet | todo | | B4, A5 |
| G-W5 Web: messaging + notif prefs (video [P2]) | 🟢 Sonnet | todo | | D1, D2, D5 |
| G-W6 Web: deep-link entry points | 🟢 Sonnet | todo | | §A1.1 |
| G-M1 Mobile: browse/search/profile | 🟢 Sonnet | todo | | B1, B2 |
| G-M2 Mobile: booking + Apple/Google Pay | 🟢 Sonnet | todo | | B3, C2 |
| G-M3 Mobile: provider dashboard + availability | 🟢 Sonnet | todo | | A4, A5 |
| G-M4 Mobile: messaging + push (video [P2]) | 🟢 Sonnet | todo | | D1, D2, D5 |
| G-M5 Mobile: deep-links + upgrade prompt at checkout | 🟢 Sonnet | todo | | §A4.1, §A14 |

## WS-X · Continuous / launch-gating

| Step | Model | Status | Branch / commit | Notes |
|---|---|---|---|---|
| X1 Vendor setup (Stripe/KYC/video) | — | todo | | gates A2, C2, D5 |
| X2 Legal & policy artefacts | — | todo | | gates A1 + launch |
| X3 App Store / Play compliance review | — | todo | | gates submission |
| X4 Tax/finance config per region | — | todo | | gates regional launch |
| X5 NFR & observability wiring | 🟢 Sonnet | todo | | reuse infra/observability |
| X6 Swiss Ephemeris commercial licence | — | todo | | hard launch gate |
