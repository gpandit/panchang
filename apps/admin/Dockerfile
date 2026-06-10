# ── Build ─────────────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /repo

RUN corepack enable && corepack prepare pnpm@9.15.0 --activate

COPY pnpm-workspace.yaml pnpm-lock.yaml package.json ./
COPY packages/ ./packages/
COPY apps/admin/package.json ./apps/admin/

RUN pnpm install --frozen-lockfile

COPY tsconfig.base.json turbo.json ./
COPY apps/admin ./apps/admin
COPY packages ./packages

ARG VITE_API_URL=https://api-staging.thepandit.app/v1
ENV VITE_API_URL=${VITE_API_URL}

RUN pnpm --filter @pandit/admin run build

# ── Runtime (Nginx) ───────────────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

COPY --from=builder /repo/apps/admin/dist /usr/share/nginx/html

# SPA fallback: all paths resolve to index.html
COPY <<'EOF' /etc/nginx/conf.d/default.conf
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /healthz {
        return 200 'ok';
        add_header Content-Type text/plain;
    }
}
EOF

EXPOSE 80

# Use 127.0.0.1, not localhost: Alpine resolves localhost to ::1 first, but
# nginx's `listen 80;` only binds IPv4, so an IPv6 connection to ::1 is refused.
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1/healthz || exit 1
