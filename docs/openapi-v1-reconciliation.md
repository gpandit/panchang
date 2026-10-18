# v1 OpenAPI reconciliation

**As of:** 2026-10-07  
**Status:** runtime inventory; the aspirational contract is not a claim of shipped
functionality.

The v1 source in [`Conversation/the-pandit-openapi-v1.yaml`](Conversation/the-pandit-openapi-v1.yaml)
describes the complete product target (145 paths / 172 operations). The running application is
the authority for what is currently exposed. This inventory is deliberately kept separate from
that target so an unimplemented endpoint cannot be mistaken for a working API.

## Runtime public surface

The following operations are registered by `services/api/src/api/main.py` under `/v1`. A status of
**partial** means that the route is callable but still has an explicitly known prototype gap (for
example, an in-memory store or a placeholder response); it does not mean the v3.0 requirement is
complete. **Planned** operations are registered only to make the intended response shape visible
and currently return `501` or a not-found placeholder.

| Path | Method | Status | Current limitation |
|---|---|---|---|
| `/v1/panchang/daily` | GET | partial | Route and view shaping exist; production PCS/cache and accuracy gates remain. |
| `/v1/panchang/month` | GET | partial | Month assembly is present; persistence/production cache gates remain. |
| `/v1/festivals` | GET | partial | Published CMS entries only; the current CMS store is in-process prototype data. |
| `/v1/festivals/{festival_id}` | GET | partial | Published CMS detail only; the current CMS store is in-process prototype data. |
| `/v1/notes` | GET, POST | partial | Durable ownership and quota checks are present; sync and production migration remain. |
| `/v1/notes/{note_id}` | GET, PUT, DELETE | partial | Durable CRUD is present; sync and production migration remain. |
| `/v1/reminders` | GET, POST | partial | Gregorian persistence is present; lunar resolution and delivery remain explicitly gated. |
| `/v1/reminders/{reminder_id}` | GET, PUT, DELETE | partial | Durable CRUD is present; scheduler delivery remains. |
| `/v1/profile` | GET, PUT | partial | Async SQLAlchemy profile/preferences persistence is present. |
| `/v1/profile/locations` | GET, POST | partial | Owned location persistence and IANA/coordinate validation are present. |
| `/v1/profile/birth-details` | GET, PUT, DELETE | partial | Sensitive values use an opaque Vault reference; production Vault storage remains. |
| `/v1/profile/birth-details/export` | GET | partial | Owner-only export is audited by the Vault boundary; production Vault storage remains. |
| `/v1/me` | GET, PUT | partial | Canonical identity/profile surface backed by the persistent user service. |
| `/v1/me` | DELETE | partial | Queues an idempotent deletion request and blocks subsequent canonical access. |
| `/v1/me/locations` | GET, POST | partial | Canonical owner-scoped location operations with tier limits and outbox events. |
| `/v1/me/locations/{location_id}` | DELETE | partial | Canonical owner-scoped location deletion with primary replacement. |
| `/v1/me/vault/birth-details` | PUT, DELETE | partial | Canonical Vault lifecycle operations; local fake only until production provider wiring. |
| `/v1/me/export` | POST | partial | Queues a durable reference-only export request; artifact worker remains. |
| `/v1/subscription` | GET | partial | Reads the authoritative durable entitlement row, falling back to basic. |
| `/v1/subscription/receipts` | POST | partial | Trusted adapter credential and replay guard are present; vendor verification adapters remain. |
| `/v1/subscription/verify-receipt` | POST | partial | Trusted adapter credential and replay guard are present; vendor verification adapters remain. |
| `/v1/pdf/jobs` | POST | partial | In-process job/storage adapters; durable queue/object storage is planned. |
| `/v1/pdf/jobs/{job_id}` | GET | partial | In-process job status only. |
| `/v1/temple/{temple_id}` | GET | partial | Separate temple configuration surface backed by an in-process store. |

The application also registers `/admin/v1/*` and `/temple/v1/*` operational surfaces. They are
intentionally not part of the public v1 contract above and are not substituted for the planned
`/v1/admin/*` paths in the aspirational document.

## Planned surface

Every path/operation in the aspirational YAML that is not listed in the runtime table above is
**planned**, including its marketplace, auth, calendar, webhook, internal PCS, and
`/v1/admin/*` paths. In particular, the aspirational `/v1/panchang/day` and
`/v1/panchang/range` paths are not aliases for the shipped `/v1/panchang/daily` and
`/v1/panchang/month` paths. The implemented `/v1/me/*` routes deliberately expose the canonical
identity surface while retaining the established `/v1/profile/*` routes, and
`/v1/calendar-jobs` is not an alias for `/v1/pdf/jobs`.

`docs/openapi.json` is a historical runtime snapshot and is marked non-canonical until it is
regenerated from the FastAPI application. The shared TypeScript package remains hand-authored as
documented in [`../packages/api-client-ts/README.md`](../packages/api-client-ts/README.md); no
generated client is updated by this reconciliation.
