# Pandit on Contabo — Setup Guide

This guide walks you through setting up your Contabo server to run the Pandit application stack.

## Prerequisites

- A provisioned Contabo server (Ubuntu 22.04 LTS recommended)
- SSH access to the server (root or sudo user)
- Your GitHub token (for pulling private images)
- SSL certificates (Cloudflare, Let's Encrypt, or self-signed)
- S3 credentials for file storage (AWS S3, Linode Object Storage, or MinIO)

## Phase 1: Automated Server Setup (5 minutes)

### 1.1 SSH into your server

```bash
ssh root@your.contabo.server.ip
```

### 1.2 Run the automated setup script

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/gpandit/pandit/main/infra/contabo-setup.sh)"
```

### 1.3 Verify Docker installation

```bash
docker --version
docker compose version
```

## Phase 2: Configuration (10 minutes)

### 2.1 Copy SSL Certificates

The deployment expects SSL certificates at `/opt/pandit-prod/infra/nginx/certs/`:

**Option A: Using Cloudflare Origin Certificate**

```bash
scp -P 22 staging.crt root@your.contabo.server.ip:/opt/pandit-prod/infra/nginx/certs/
scp -P 22 staging.key root@your.contabo.server.ip:/opt/pandit-prod/infra/nginx/certs/
ssh root@your.contabo.server.ip
chmod 600 /opt/pandit-prod/infra/nginx/certs/staging.*
```

**Option B: Using Let's Encrypt (certbot)**

```bash
ssh root@your.contabo.server.ip
apt-get install -y certbot
certbot certonly --standalone -d api.pandit.xyz -d pandit.xyz -d www.pandit.xyz \
  -d admin.pandit.xyz -d temple.pandit.xyz -d grafana.pandit.xyz \
  -n --agree-tos -m your-email@example.com
cp /etc/letsencrypt/live/pandit.xyz/fullchain.pem /opt/pandit-prod/infra/nginx/certs/staging.crt
cp /etc/letsencrypt/live/pandit.xyz/privkey.pem /opt/pandit-prod/infra/nginx/certs/staging.key
chmod 600 /opt/pandit-prod/infra/nginx/certs/staging.*
```

### 2.2 Configure Environment Variables

```bash
ssh root@your.contabo.server.ip
nano /opt/pandit-prod/.env.staging
```

Fill in:
- POSTGRES_PASSWORD — Strong random password (20+ chars)
- REDIS_PASSWORD — Strong random password (20+ chars)
- API_SECRET_KEY — Run: `python3 -c "import secrets; print(secrets.token_hex(32))"`
- S3_* — Your storage credentials
- GRAFANA_ADMIN_PASSWORD — Strong password
- SLACK_WEBHOOK_URL — Optional (alerts)

Then secure it:

```bash
chmod 600 /opt/pandit-prod/.env.staging
```

### 2.3 Configure Docker Registry Access

```bash
ssh root@your.contabo.server.ip
cat > ~/.docker/config.json << 'EOF'
{
  "auths": {
    "ghcr.io": {
      "auth": "BASE64_ENCODED_TOKEN_HERE"
    }
  }
}
EOF
chmod 600 ~/.docker/config.json

# Generate base64 token: echo -n "USERNAME:GITHUB_TOKEN" | base64
```

## Phase 3: Initial Deployment (10 minutes)

### 3.1 Pull latest images

```bash
ssh root@your.contabo.server.ip
cd /opt/pandit-prod
git fetch origin main && git reset --hard origin/main

IMAGE_REGISTRY=ghcr.io/gpandit \
IMAGE_TAG=staging-latest \
  docker compose --env-file .env.staging -f infra/docker-compose.staging.yml pull
```

### 3.2 Start infrastructure services first

```bash
IMAGE_REGISTRY=ghcr.io/gpandit \
IMAGE_TAG=staging-latest \
  docker compose --env-file .env.staging -f infra/docker-compose.staging.yml \
    up -d postgres redis otel-collector prometheus alertmanager
sleep 30
docker compose -f infra/docker-compose.staging.yml ps
```

### 3.3 Run database migrations

```bash
IMAGE_REGISTRY=ghcr.io/gpandit \
IMAGE_TAG=staging-latest \
  docker compose --env-file .env.staging -f infra/docker-compose.staging.yml \
    run --rm api python -m alembic upgrade head
```

### 3.4 Start application services

```bash
IMAGE_REGISTRY=ghcr.io/gpandit \
IMAGE_TAG=staging-latest \
  docker compose --env-file .env.staging -f infra/docker-compose.staging.yml \
    up -d panchang api worker web admin temple-admin nginx grafana
```

### 3.5 Verify deployment

```bash
docker compose -f infra/docker-compose.staging.yml ps
curl -k https://api.pandit.xyz/health
curl -k https://pandit.xyz/
```

## Phase 4: GitHub Actions Setup (5 minutes)

Go to GitHub → Settings → Secrets and variables → Actions

Add these secrets:

```
CONTABO_HOST              = your.contabo.server.ip
CONTABO_SSH_USER          = root
CONTABO_SSH_KEY           = (private SSH key)
IMAGE_REGISTRY            = ghcr.io/gpandit
STAGING_DATABASE_URL      = postgresql+psycopg://pandit:PASSWORD@IP:5432/pandit_staging
```

### Generate SSH key:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/contabo-deploy -N ""
cat ~/.ssh/contabo-deploy.pub | ssh root@CONTABO_IP 'cat >> ~/.ssh/authorized_keys'
cat ~/.ssh/contabo-deploy  # Copy to GitHub secret
```

## Troubleshooting

### Images won't pull (auth error)

```bash
docker login ghcr.io -u USERNAME -p TOKEN
cat ~/.docker/config.json
```

### Services won't start

```bash
docker compose -f infra/docker-compose.staging.yml logs postgres
docker compose -f infra/docker-compose.staging.yml logs api
docker compose -f infra/docker-compose.staging.yml restart api
```

### Database migrations fail

```bash
docker compose -f infra/docker-compose.staging.yml exec postgres \
  psql -U pandit -d pandit_staging -c "SELECT version();"
```

### Out of disk space

```bash
df -h
docker image prune -a
docker container prune
```

## Backup PostgreSQL

```bash
cd /opt/pandit-prod
docker compose -f infra/docker-compose.staging.yml exec postgres \
  pg_dump -U pandit pandit_staging > backup_$(date +%Y%m%d).sql
```

## Monitor & Logs

```bash
# All services
docker compose -f infra/docker-compose.staging.yml logs -f

# Specific service
docker compose -f infra/docker-compose.staging.yml logs -f api

# Access Grafana
# URL: https://grafana.pandit.xyz
# Username: admin
# Password: (check .env.staging GRAFANA_ADMIN_PASSWORD)
```

See **CONTABO_MIGRATION_OVERVIEW.md** for architecture details and **CONTABO_MIGRATION_CHECKLIST.md** for step-by-step checklist.
