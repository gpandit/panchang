---
name: project-api-gateway
description: Step 3.1 API gateway — what was built, what's stubbed, upgrade notes for production
metadata:
  type: project
---

Step 3.1 complete. Versioned REST/JSON gateway built in `services/api`, commit `36b1329`.

**Why:** Single public API surface for web, iOS, Android, admin (Architecture §3).

**What's built:**
- `/v1/panchang/daily` + `/v1/panchang/month` (Silver+)
- `/v1/festivals`, `/v1/notes`, `/v1/reminders` (Silver+), `/v1/profile`, `/v1/subscription`, `/v1/pdf/jobs` (Gold+)
- JWT HS256 auth (`services/api/src/api/auth.py`) — swap to RS256/JWKS for production
- Sliding-window rate limiter (in-memory) — swap to Redis for multi-replica prod
- In-process LRU cache + `Cache-Control` headers for Panchang hot path
- OpenAPI schema at `docs/openapi.json`; `packages/api-client-ts` has typed models + fetch client

**What's stubbed (TODO markers):**
- Festival, notes, reminders, profile, PDF endpoints return empty/501 — downstream services wired in later steps
- Profile always returns stub data from JWT claims; real DB query deferred to step 3.4

**How to apply:** When wiring downstream services in later steps, look for `TODO(step-3.x)` comments in the router files.
