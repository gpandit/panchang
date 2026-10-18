# Codex review memory

Use this workspace-local memory when reviewing or extending PR #106 / S2-01
identity and Vault work. The Codex findings below were accepted and fixed.

## Accepted findings and resolutions

### RLS context before owned writes

The identity resolver must set PostgreSQL's transaction-local `app.user_id`
after resolving or creating the user and before reading or writing RLS-protected
tables. `IdentityService.resolve` now does this with `set_config(..., true)`;
new-user preference creation happens only after the context is set. Migration
`0006_s201_identity_lifecycle` also applies forced RLS to `user_jobs`.

### Canonical profile PATCH

The v1 contract requires `PATCH /v1/me`. The route is registered and tested;
`PUT /v1/me` remains as a compatibility operation. Runtime reconciliation JSON
and Markdown list the PATCH operation.

### Atomic export/deletion job replay

Open export/deletion jobs are serialized by locking the owning user row. The
`user_jobs` table has a partial unique index for `(user_id, kind)` while status
is `queued` or `processing`, and job plus outbox creation uses a savepoint with
`IntegrityError` recovery to return the winning job during a concurrent retry.

### Atomic location quota and primary mutation

Location add/delete operations lock the owning user row before counting,
checking tier limits, changing the primary flag, selecting a replacement, or
inserting/deleting a location. The existing unique primary index remains the
database backstop.

### Lifecycle migration constraints

Migration `0006_s201_identity_lifecycle` backfills null status values, makes
`users.status` non-null, adds `ck_users_status`, keeps deletion timestamps
nullable, and creates the open-job index and user-job RLS policy. Migration
tests assert the resulting constraints and index.

## Evidence

- Fix commit: `d998750 fix: address S2-01 PR review findings`
- CI workflow commit: `a3c4b9a ci: run full hosted suite for develop PRs`
- Local API suite: 130 passed, 5 skipped
- Local Ruff, format, and mypy checks passed
- GitHub-hosted PR checks passed on PR #106
