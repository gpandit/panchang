#!/bin/bash
# Contabo Server Initial Setup Script
# Run this ONCE on a fresh Contabo server to prepare it for Pandit deployment
# Usage: curl -sSL https://raw.githubusercontent.com/.../contabo-setup.sh | bash
# Or locally: bash infra/contabo-setup.sh

set -euo pipefail

echo "=== Pandit Contabo Server Setup ==="
echo "Setting up Docker, Docker Compose, Git, and system dependencies..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Update system packages
echo -e "${YELLOW}[1/7] Updating system packages...${NC}"
apt-get update
apt-get upgrade -y

# Install required tools
echo -e "${YELLOW}[2/7] Installing required tools...${NC}"
apt-get install -y \
  curl \
  wget \
  git \
  ca-certificates \
  gnupg \
  lsb-release \
  software-properties-common \
  htop \
  tmux \
  vim \
  openssl

# Install Docker
echo -e "${YELLOW}[3/7] Installing Docker...${NC}"
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
rm get-docker.sh

# Add current user to docker group (so you don't need sudo)
usermod -aG docker $(whoami) || true

# Install Docker Compose (included with modern Docker, but ensure it's there)
echo -e "${YELLOW}[4/7] Verifying Docker Compose...${NC}"
docker compose version || echo "Docker Compose should be pre-installed"

# Create deploy directory
echo -e "${YELLOW}[5/7] Creating deployment directories...${NC}"
mkdir -p /opt/pandit-prod
cd /opt/pandit-prod

# Clone the repository (if not already present)
if [ ! -d .git ]; then
  echo "Cloning repository..."
  git clone https://github.com/gpandit/pandit.git . 2>/dev/null || true
fi

# Create directories for certificates and environment files
mkdir -p infra/nginx/certs

# Create .env.staging if it doesn't exist (template only - will be updated by deploy)
if [ ! -f .env.staging ]; then
  echo -e "${YELLOW}[6/7] Creating .env.staging template...${NC}"
  cat > .env.staging << 'ENVEOF'
# Staging environment — FILL IN REAL VALUES BEFORE FIRST DEPLOY
IMAGE_REGISTRY=ghcr.io/gpandit
IMAGE_TAG=staging-latest
POSTGRES_DB=pandit_staging
POSTGRES_USER=pandit
POSTGRES_PASSWORD=CHANGE_ME_TO_STRONG_PASSWORD
REDIS_PASSWORD=CHANGE_ME_TO_STRONG_PASSWORD
API_SECRET_KEY=CHANGE_ME_64_random_bytes_hex
S3_ENDPOINT_URL=https://s3.amazonaws.com
S3_ACCESS_KEY=CHANGE_ME
S3_SECRET_KEY=CHANGE_ME
S3_BUCKET=pandit-staging
GRAFANA_ADMIN_PASSWORD=CHANGE_ME_TO_STRONG_PASSWORD
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/CHANGE_ME
PANCHANG_BUILD_PROFILE=staging
PANCHANG_EPHEMERIS_LICENSE=agpl
ENVEOF
  chmod 600 .env.staging
  echo -e "${RED}⚠️  .env.staging created — update credentials before first deploy!${NC}"
fi

# Setup Docker log rotation to prevent disk fill
echo -e "${YELLOW}[7/7] Configuring Docker logging...${NC}"
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'JSONEOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "20m",
    "max-file": "5"
  }
}
JSONEOF
systemctl daemon-reload
systemctl restart docker

# Set proper permissions
chown -R $(whoami):$(whoami) /opt/pandit-prod
chmod 700 /opt/pandit-prod

echo -e "${GREEN}=== Setup Complete ===${NC}"
echo ""
echo "Next steps:"
echo "1. Copy SSL certificates to: /opt/pandit-prod/infra/nginx/certs/staging.crt and staging.key"
echo "2. Update .env.staging with real credentials at: /opt/pandit-prod/.env.staging"
echo "3. Update GitHub Actions secrets (see contabo-deploy.yml setup instructions)"
echo "4. Commit and push: git add infra/contabo-setup.sh"
echo ""
echo "To manually start services:"
echo "  cd /opt/pandit-prod"
echo "  docker compose --env-file .env.staging -f infra/docker-compose.staging.yml pull"
echo "  docker compose --env-file .env.staging -f infra/docker-compose.staging.yml up -d"
