# Contabo Migration Checklist

Complete these steps to migrate from DigitalOcean to Contabo.

## Pre-Migration (Before you start)

- [ ] Contabo server provisioned and accessible via SSH
- [ ] Have your GitHub personal access token (for image registry)
- [ ] Have SSL certificates ready (Cloudflare Origin or Let's Encrypt)
- [ ] Have S3 credentials (or object storage alternative)
- [ ] Note your Contabo server IP/DNS name

## Phase 1: Initial Server Setup (5 min)

### On the Contabo server (SSH):

```bash
# Run automated setup (installs Docker, Docker Compose, creates directories)
bash -c "$(curl -fsSL https://raw.githubusercontent.com/gpandit/pandit/main/infra/contabo-setup.sh)"

# Verify Docker installation
docker --version
docker compose version
```

- [ ] Docker installed successfully
- [ ] Docker Compose installed successfully
- [ ] `/opt/pandit-prod/` directory created

## Phase 2: SSL Certificates (3 min)

Choose one:

### Option A: Cloudflare Origin Certificate

```bash
# Copy from your local machine to server
scp -P 22 ~/Downloads/staging.crt root@CONTABO_IP:/opt/pandit-prod/infra/nginx/certs/
scp -P 22 ~/Downloads/staging.key root@CONTABO_IP:/opt/pandit-prod/infra/nginx/certs/

# SSH and fix permissions
ssh root@CONTABO_IP
chmod 600 /opt/pandit-prod/infra/nginx/certs/staging.*
```

### Option B: Let's Encrypt (on server)

```bash
# SSH into server
ssh root@CONTABO_IP

# Install and generate
apt-get install -y certbot
certbot certonly --standalone \
  -d api.pandit.xyz -d pandit.xyz -d www.pandit.xyz \
  -d admin.pandit.xyz -d temple.pandit.xyz -d grafana.pandit.xyz \
  -n --agree-tos -m your-email@example.com

# Copy to nginx directory
cp /etc/letsencrypt/live/pandit.xyz/fullchain.pem /opt/pandit-prod/infra/nginx/certs/staging.crt
cp /etc/letsencrypt/live/pandit.xyz/privkey.pem /opt/pandit-prod/infra/nginx/certs/staging.key
chmod 600 /opt/pandit-prod/infra/nginx/certs/staging.*
```

- [ ] `staging.crt` exists at `/opt/pandit-prod/infra/nginx/certs/`
- [ ] `staging.key` exists at `/opt/pandit-prod/infra/nginx/certs/`
- [ ] Permissions are `600` on both files

## Phase 3: Environment Configuration (5 min)

On the Contabo server:

```bash
ssh root@CONTABO_IP
nano /opt/pandit-prod/.env.staging
```

Update these values - see CONTABO_MIGRATION_OVERVIEW.md for full details.

- [ ] `.env.staging` has been updated with real credentials
- [ ] Strong passwords have been used (20+ characters)
- [ ] S3 credentials are valid
- [ ] File permissions are `600`

## Phase 4: Docker Registry Setup (2 min)

See CONTABO_SETUP.md for detailed instructions on GHCR authentication.

- [ ] Docker registry credentials configured
- [ ] `docker login ghcr.io` succeeds

## Phase 5: Initial Deployment (10 min)

See CONTABO_SETUP.md Phase 3 for complete step-by-step instructions.

- [ ] All containers are running
- [ ] PostgreSQL is healthy
- [ ] Redis is healthy
- [ ] Migrations ran successfully
- [ ] API service is running

## Phase 6: GitHub Actions Secrets (5 min)

Go to your GitHub repo → Settings → Secrets and variables → Actions

Required secrets:
- `CONTABO_HOST` — Your server IP or DNS name
- `CONTABO_SSH_USER` — SSH user (usually `root`)
- `CONTABO_SSH_KEY` — Private SSH key for deployment
- `IMAGE_REGISTRY` — `ghcr.io/gpandit`
- `STAGING_DATABASE_URL` — PostgreSQL connection string

- [ ] All GitHub secrets configured
- [ ] SSH public key added to server

## Phase 7: First Automated Deployment (5 min)

Go to GitHub → Actions → Contabo Deploy → Run workflow

- [ ] All build/deploy steps pass
- [ ] Smoke checks pass

## Phase 8: Verify Live Services (3 min)

- [ ] https://pandit.xyz/ loads successfully
- [ ] https://api.pandit.xyz/ returns 200 or 404
- [ ] All services are accessible

## Phase 9: DNS & Final Cutover

Update DNS records to point to Contabo IP and verify propagation.

- [ ] DNS records updated
- [ ] DNS propagation verified

## Phase 10: Post-Migration

- [ ] Old DigitalOcean server backed up (if needed)
- [ ] Grafana dashboard is accessible
- [ ] Alerts are configured

---

See **CONTABO_SETUP.md** for detailed instructions and troubleshooting guides.
