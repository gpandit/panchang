# apps/temple-admin — The Pandit Temple Admin Console

Served at **`temple.pandit.xyz`**.

Stack: React · TypeScript · Vite

A temple staff member logs in with email + password and manages the temple a
superuser assigned to them: the **session location** (lat/lon/tz, which drives
tithi computation on the Temple Display), the **aarti schedule**, and a list of
**events / announcements**.

Connects to `services/api`:

- `POST /temple/v1/auth/login` — email + password → JWT (carries `temple_id`)
- `GET  /temple/v1/auth/me` — the caller's assigned temple
- `GET  /temple/v1/temple` / `PUT /temple/v1/temple` — read / update config

The public Temple Display (`apps/web` at `/display?temple=<id>`) reads the same
config via `GET /v1/temple/{id}`. Superusers provision temples and admin logins
via `POST /admin/v1/temples` and `POST /admin/v1/temples/{id}/admins`.

## Local dev

```bash
pnpm --filter @pandit/temple-admin dev   # http://localhost:3002 (proxies /temple + /v1 → :8000)
```

Seeded demo login (dev only): `admin@siddhivinayak.temple` / `templeadmin`.
