# Contabo Migration Overview

## Architecture Overview

```
GitHub (Main Branch)
    ↓
    ├─→ CI Pipeline (tests, linting)
    │
    └─→ Contabo Deploy Workflow
        ├─→ 1. Build Docker images (all services)
        ├─→ 2. Push to GitHub Container Registry (GHCR)
        ├─→ 3. Run database migrations (Alembic)
        ├─→ 4. SSH into Contabo + docker compose up
        ├─→ 5. Smoke tests (health checks)
        └─→ 6. Load tests (optional)
```

## Infrastructure Stack

### Services Running on Contabo

**Infrastructure:**
- PostgreSQL 16 — Main database
- Redis 7 — Cache + message queue
- OpenTelemetry Collector — Traces collection
- Prometheus — Metrics storage
- Grafana — Dashboards
- AlertManager — Alert routing

**Applications:**
- panchang (Python) — Vedic calendar service
- api (Python FastAPI) — REST API, bookings, temple admin
- worker — Async jobs (PDF, reminders, cache)
- web (Next.js) — Public website
- admin (Vite React) — Admin console
- temple-admin (Vite React) — Temple admin
- nginx — Reverse proxy (SSL termination)

### Network Layout

```
Internet (HTTPS)
    ↓
Nginx (ports 80, 443)
    ├─→ api.pandit.xyz → FastAPI (8000)
    ├─→ pandit.xyz → Next.js (3000)
    ├─→ admin.pandit.xyz → Vite (80)
    ├─→ temple.pandit.xyz → Vite (80)
    └─→ grafana.pandit.xyz → Grafana (3000)

All internal communication via Docker bridge network
```

## Deployment Process

### 1. Code Push → GitHub

```bash
git push origin main
```

Triggers CI pipeline (tests pass required).

### 2. Build Phase

GitHub Actions runner builds Docker images:

```bash
docker build -t ghcr.io/gpandit/pandit-api:COMMIT_SHA services/api/
docker build -t ghcr.io/gpandit/pandit-web:COMMIT_SHA apps/web/
# ... etc
```

Tags applied:
- `COMMIT_SHA` (immutable, unique)
- `staging-latest` (mutable, tracks newest)

### 3. Database Migrations

Runs once before deployment:

```bash
docker run pandit-api python -m alembic upgrade head
```

Idempotent — safe to run multiple times.

### 4. Deployment

SSH into Contabo server and:

```bash
# Pull latest code
git fetch origin main && git reset --hard origin/main

# Pull new images
docker compose pull

# Start infrastructure (postgres, redis, observability)
docker compose up -d postgres redis otel-collector prometheus

# Wait 15 seconds for stability
sleep 15

# Start applications (rolling restart)
docker compose up -d panchang api worker web admin temple-admin nginx
```

### 5. Post-Deployment

Smoke tests verify all services are healthy:

```bash
curl https://api.pandit.xyz/health
curl https://pandit.xyz/
```

## Key Design Decisions

### 1. Environment Variables on Server

`.env.staging` is NOT overwritten by CI. This prevents:
- Accidental credential leaks
- Service crashes from missing env vars
- Overwriting credentials intentionally changed on server

**Update credentials directly on server** if they change.

### 2. Rolling Restart Strategy

1. Infrastructure first (postgres, redis) — 15 second wait
2. Application services next (api, workers, web)

Prevents:
- Connection failures (postgres not ready)
- Data corruption (workers before migrations)
- Cascading failures

### 3. Immutable Docker Images

Every commit produces a unique, immutable image tagged with `COMMIT_SHA`.

Benefits:
- Fast rollback (deploy old SHA)
- Reproducible builds
- CI caching (reused layers)

### 4. Health Checks Built-in

All services have Docker health checks that validate startup:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 15s
  timeout: 5s
  retries: 3
```

### 5. Observability Built-in

All services emit:
- **Logs** — JSON format, 20MB rotating
- **Traces** — OpenTelemetry (OTLP)
- **Metrics** — Prometheus scrape format

Feeds into Grafana dashboards.

## DigitalOcean vs Contabo

| Aspect | Both Use Same |
|--------|---------------|
| Docker Compose | Same file (docker-compose.staging.yml) |
| GitHub Actions | Same deployment flow |
| Image Registry | GHCR (GitHub Container Registry) |
| Databases | PostgreSQL + Redis |
| SSL | Cloudflare or Let's Encrypt |
| Storage | S3 (AWS or compatible) |

**Only the server IP/hostname changes.**

## Capacity Planning

### Recommended Specs

**Staging/Small Production:**
- CPU: 4+ cores
- RAM: 8+ GB
- Disk: 100+ GB

**Resource Usage:**

```
PostgreSQL:         500 MB - 2 GB (data size dependent)
Redis:              100 MB - 500 MB
API service:        ~300 MB
Panchang:           ~500 MB
Worker:             ~200 MB
Web/Admin:          50-100 MB each
Nginx:              ~50 MB
Observability:      500 MB - 1 GB

Idle:               3-5 GB
Peak load:          6-8 GB
```

**For 8 GB server:** Suitable for staging/small production
**For 16 GB server:** Better for production with traffic spikes

## Monitoring

### Grafana Access

```
URL: https://grafana.pandit.xyz
User: admin
Password: (from .env.staging GRAFANA_ADMIN_PASSWORD)
```

Pre-built dashboards show:
- Request rates/latency by endpoint
- Error rates
- Database pool status
- Redis memory usage
- Container CPU/memory

### Slack Alerts (Optional)

If `SLACK_WEBHOOK_URL` is set, AlertManager posts:
- Service down (restart loops)
- Database errors
- High memory/CPU usage

### Manual Log Inspection

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f postgres
docker compose logs -f nginx
```

## Disaster Recovery

### Backup Database

```bash
docker compose exec postgres \
  pg_dump -U pandit pandit_staging > backup_$(date +%Y%m%d).sql
```

### Restore Database

```bash
# Stop services
docker compose down

# Remove volume
docker volume rm pandit-prod_postgres_data

# Start postgres
docker compose up -d postgres
sleep 30

# Restore
cat backup_20260625.sql | docker compose exec -T postgres \
  psql -U pandit pandit_staging

# Restart all
docker compose up -d
```

## Common Troubleshooting

### "Images won't pull"

```bash
docker login ghcr.io -u USERNAME -p GITHUB_TOKEN
docker compose pull
```

### "Service won't start (health check failed)"

```bash
docker compose logs postgres
docker compose logs api

# If postgres: check volume permissions
ls -la /var/lib/docker/volumes/pandit-prod_postgres_data/

# If api: test database connection
docker compose exec api python -c "import psycopg; print('OK')"
```

### "Out of disk space"

```bash
df -h
docker image prune -a
docker container prune
du -sh /var/lib/docker/volumes/
```

## Automation Explained

### GitHub Actions Workflow

The `.github/workflows/contabo-deploy.yml` file:

1. **On every push to main:** Automatically builds and deploys
2. **On manual trigger:** Allows specifying custom image tag

### SSH Deployment

Uses `appleboy/ssh-action` to connect via SSH key and run deployment commands.

```yaml
- uses: appleboy/ssh-action@v1
  with:
    host: CONTABO_IP
    username: root
    key: PRIVATE_KEY
    script: |
      cd /opt/pandit-prod
      docker compose pull
      docker compose up -d
```

### Environment Variables Passed

```bash
IMAGE_TAG=abc123def456
IMAGE_REGISTRY=ghcr.io/gpandit
docker compose --env-file .env.staging up -d
```

Merges:
- `IMAGE_TAG` and `IMAGE_REGISTRY` from workflow
- `.env.staging` from server (credentials, S3, etc.)

## Next Steps

1. Run automated setup: `bash infra/contabo-setup.sh`
2. Configure `.env.staging` and SSL certs
3. Add GitHub secrets
4. Manually test initial deployment (Phase 3 of CONTABO_SETUP.md)
5. Push to main to trigger automated deployment
6. Monitor Grafana dashboard

See **CONTABO_MIGRATION_CHECKLIST.md** for detailed checklist.
