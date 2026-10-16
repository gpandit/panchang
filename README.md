# The Pandit

Location-accurate Hindu Panchang, calendar, planning and spiritual-lifestyle platform.

> **Engine first. Green CI gates every step.**
> Nothing ships until the Panchang accuracy harness passes on every merge.

---

## Repository layout

```
/
├── apps/
│   ├── web/        Next.js App Router + TypeScript + Tailwind   (Stage 3)
│   ├── admin/      React admin console                           (Stage 3)
│   ├── ios/        Native Swift + SwiftUI                        (Stage 3)
│   └── android/    Native Kotlin + Jetpack Compose              (Stage 3)
│
├── services/
│   ├── panchang/   FastAPI — Panchang Computation Service        (Stage 1)
│   └── api/        FastAPI — API Gateway + domain modules        (Stage 2)
│
├── packages/
│   ├── design-tokens/    Token placeholder (Aqualeo design system)
│   └── api-client-ts/    Shared TypeScript API types & client
│
├── libs/
│   └── ephemeris/        Swiss Ephemeris data files              (Step 0.2)
│
├── infra/
│   └── docker-compose.yml   Local Postgres + Redis + MinIO
│
├── tools/                   Scripts, codegen, harness runners
└── prompts/                 Build prompts and project context
```

---

## Toolchains

| Layer     | Tool          | Purpose                               |
|-----------|---------------|---------------------------------------|
| Python    | **uv**        | Package management (workspace)        |
| Python    | **ruff**      | Lint + format (`services/`)           |
| Python    | **mypy**      | Static type checking                  |
| Python    | **pytest**    | Unit and integration tests            |
| JS / TS   | **pnpm**      | Package management (workspace)        |
| JS / TS   | **Turborepo** | Task orchestration across packages    |
| JS / TS   | **ESLint**    | Linting (`apps/`, `packages/`)        |
| JS / TS   | **Prettier**  | Formatting                            |
| JS / TS   | **tsc**       | Type checking                         |
| JS / TS   | **Vitest**    | Unit and integration tests            |
| Git hooks | **pre-commit**| Ruff + Prettier + secret scanning     |
| CI        | **GitHub Actions** | lint · typecheck · test on every push |

---

## Prerequisites

- **Node.js** 20+
- **pnpm** 9+ (`npm install -g pnpm`)
- **Python** 3.12+
- **uv** ([install](https://docs.astral.sh/uv/getting-started/installation/))
- **Docker** (for local infrastructure)
- **pre-commit** (`pip install pre-commit` or `brew install pre-commit`)

---

## Quick start

### 1. Install dependencies

```bash
# TypeScript / JS workspace
pnpm install

# Python workspace
uv sync --all-packages --dev

# Git hooks
pre-commit install
```

### 2. Start local infrastructure

```bash
# Start PostGIS-backed Postgres, Redis, MinIO, migrations, API, and PCS
./deploy.sh up

# Verify health
./deploy.sh status
```

Services once running:

| Service  | URL / port                             |
|----------|----------------------------------------|
| PostgreSQL/PostGIS | `localhost:5432`  db=`pandit_dev`      |
| Redis    | `localhost:6379`                       |
| MinIO    | API `localhost:9000`, console `:9001`  |

`API_DATABASE_URL` and `PANCHANG_DATABASE_URL` both point at the same local
**PostgreSQL 16 + PostGIS** database. PostGIS is required by the v3 migrations
and location/booking geography types; plain `postgres:16-alpine` is not enough.
Redis uses database 0 for the API and database 1 for PCS. MinIO provides the
local S3-compatible object-storage endpoint.

To stop the development deployment while preserving Docker volumes:

```bash
./deploy.sh down
```

### 3. Run the Python services manually (optional)

```bash
# API Gateway
cd services/api
uv run uvicorn api.main:app --reload --port 8000

# Panchang Computation Service
cd services/panchang
uv run uvicorn panchang.main:app --reload --port 8001
```

### 4. Run the web app (placeholder until Stage 3)

```bash
# Not yet scaffolded — see apps/web/README.md
```

---

## Root scripts

These fan out to all workspaces:

```bash
# Lint everything
pnpm run ci:lint

# Type-check everything
pnpm run ci:typecheck

# Run all tests
pnpm run ci:test

# Format check
pnpm run ci:format:check

# Python only
pnpm run py:lint
pnpm run py:typecheck
pnpm run py:test
pnpm run py:format
```

---

## CI

GitHub Actions runs once for each push and runs a separate full validation for
promotion pull requests targeting `staging` or `main` (`.github/workflows/ci.yml`):

The self-hosted workflow is manual-only and is not part of automatic push or
pull-request validation.

1. **python-ci** — ruff lint/format-check, mypy, pytest across `services/`
2. **typescript-ci** — ESLint, Prettier check, tsc, Vitest across `packages/` and `apps/`
3. **accuracy-harness** — *skipped placeholder* (enabled in Step 1.3; will gate all merges)
4. **all-checks-pass** — aggregated gate for branch protection rules

---

## Design system note

The `packages/design-tokens/tokens.placeholder.json` file contains `TODO(design)` placeholders for every visual token. **Do not fill in real values.** The Aqualeo design system will replace this file in Stage 3. All components must reference tokens by name only — never hardcode colours, fonts, or spacing.

---

## Secrets management

- `.env.example` is committed; `.env` is not.
- Dev defaults are set in `.env.example` — they are safe for local use only.
- Staging and production secrets live in the managed secret store (e.g. AWS Secrets Manager / GCP Secret Manager). See `CONTRIBUTING.md §4`.
- The Swiss Ephemeris **commercial licence** is a hard gate before any public launch. See `libs/ephemeris/README.md`.
# pandit-xyz
