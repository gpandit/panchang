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
| `/v1/notes` | GET | partial | Returns an empty prototype list; DB persistence is not wired. |
| `/v1/notes` | POST | planned | Returns `501 Not Implemented`. |
| `/v1/notes/{note_id}` | GET, PUT, DELETE | planned | Placeholder not-found responses. |
| `/v1/reminders` | GET | partial | Returns an empty prototype list; scheduler persistence is not wired. |
| `/v1/reminders` | POST | planned | Returns `501 Not Implemented`. |
| `/v1/reminders/{reminder_id}` | DELETE | planned | Placeholder not-found response. |
| `/v1/profile` | GET | partial | Claims-backed projection; profile persistence is not wired. |
| `/v1/profile` | PUT | planned | Returns `501 Not Implemented`. |
| `/v1/profile/locations` | GET | partial | Returns an empty prototype list; persistence is not wired. |
| `/v1/profile/locations` | POST | planned | Returns `501 Not Implemented`. |
| `/v1/subscription` | GET | partial | Reads signed claims; receipt reconciliation is not wired. |
| `/v1/pdf/jobs` | POST | partial | In-process job/storage adapters; durable queue/object storage is planned. |
| `/v1/pdf/jobs/{job_id}` | GET | partial | In-process job status only. |
| `/v1/temple/{temple_id}` | GET | partial | Separate temple configuration surface backed by an in-process store. |

The application also registers `/admin/v1/*` and `/temple/v1/*` operational surfaces. They are
intentionally not part of the public v1 contract above and are not substituted for the planned
`/v1/admin/*` paths in the aspirational document.

## Planned surface

Every path/operation in the aspirational YAML that is not listed in the runtime table above is
**planned**, including its marketplace, auth, calendar, user `/me`, webhook, internal PCS, and
`/v1/admin/*` paths. In particular, the aspirational `/v1/panchang/day` and
`/v1/panchang/range` paths are not aliases for the shipped `/v1/panchang/daily` and
`/v1/panchang/month` paths. Likewise, `/v1/me/*` is not an alias for `/v1/profile/*`, and
`/v1/calendar-jobs` is not an alias for `/v1/pdf/jobs`.

`docs/openapi.json` is a historical runtime snapshot and is marked non-canonical until it is
regenerated from the FastAPI application. The shared TypeScript package remains hand-authored as
documented in [`../packages/api-client-ts/README.md`](../packages/api-client-ts/README.md); no
generated client is updated by this reconciliation.
