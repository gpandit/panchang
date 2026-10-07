# Build Status — Pandit Services Marketplace

## v3.0 orchestrator progress

This section records the ordered v3.0 build-dashboard implementation run. It is
kept separate from the legacy marketplace workstream below. A package is marked
done only after its focused checks and code review have completed; real service,
vendor, and commercial-licence gates remain explicit until verified.

| Package | Status | Evidence / next action |
|---|---|---|
| S0-01 ADRs and architecture decisions | done | `docs/adr/0001`–`0009`; documentation structure and link checks passed. |
| S0-02 FastAPI/OpenAPI reconciliation | done | Canonical aspirational contract plus 20-operation runtime inventory and drift tests; generated clients remain deferred until target/runtime convergence, not claimed complete. |
| S0-03 SQLAlchemy async/PostgreSQL foundation | done | Driver normalization, injectable Alembic seam, isolated migration smoke test, and URL coverage reviewed; live Postgres/PostGIS integration remains an external gate. |
| S0-04 v3 data-model migrations | done | Additive revision `0002_v3_data_model` registers 56 tables with local privacy, uniqueness, money, ledger, and booking-overlap checks; live Postgres/PostGIS migration remains an external gate. |
| S0-05 outbox/idempotency/Vault interfaces | done | Revision `0003_s005_outbox_idempotency`, opaque event refs, scoped replay guards, deterministic Vault fake, and payload-free access logging reviewed; workers/external Vault remain later gates. |
| S0-06 contract and authority checks | done | Offline checker and 7 unit tests pass and run in Python CI; runtime-route inventory drift is guarded. Generated-client drift is deferred until S0-02 target/runtime convergence, not claimed complete. |
| S0-07 Postgres/Redis integration | done | CI run 37548797298 passed the ephemeral PostGIS/Redis job, migrations, user/outbox readback, cache/lock test, and fixture latency observation; production SLO evidence remains a later gate. |

**S0 gate (2026-10-07):** Passed the defined foundation checks in
`https://github.com/gpandit/panchang/actions/runs/37548797298` (Python,
TypeScript, four-fixture accuracy regression, PostGIS/Redis integration, and
all-checks-pass). The S1 accuracy dataset gate remains **not passed**: four
fixtures are not 500 days across ten locations. The aspirational v1 OpenAPI is
not a claim that its planned routes or generated clients are shipped. Production
Vault, licensing, load/SLO and provider integrations remain open.

| Package | Status | Evidence / next action |
|---|---|---|
| S1-01 PCS ephemeris boundary | done | `services/panchang/src/panchang/engine.py` is the sole library importer; CI guard and regressions pass. Local Ruff/format/mypy and 165 tests passed; four accuracy fixtures passed. Calibration, flagged polar fallback, and 500-day/10-location gate remain S1 work. |

**S0 CI repair (2026-10-07):** Python 3.12 local checks passed after Ruff,
format, mypy, and pytest import-path fixes: `uv run ruff check services/`,
`uv run ruff format --check services/`, `uv run mypy services/ --config-file
pyproject.toml`, and `uv run pytest services/ tools/ -v --tb=short` (159 tests,
21 subtests). Remote CI and real PostgreSQL/PostGIS/Redis checks still require
independent evidence; no S0 stage gate is claimed passed yet.

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
| F2 Marketplace schema + no-double-booking constraint | 🔴 Opus | todo | | depends F1 |
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
