# ── Dependency install ────────────────────────────────────────────────────────
FROM node:20-alpine AS deps

WORKDIR /repo

RUN corepack enable && corepack prepare pnpm@9.15.0 --activate

# Workspace manifests for cache efficiency
COPY pnpm-workspace.yaml pnpm-lock.yaml package.json ./
COPY packages/ ./packages/
COPY apps/web/package.json ./apps/web/

RUN pnpm install --frozen-lockfile

# ── Build ─────────────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /repo

RUN corepack enable && corepack prepare pnpm@9.15.0 --activate

COPY --from=deps /repo/node_modules ./node_modules
COPY --from=deps /repo/packages ./packages

COPY pnpm-workspace.yaml pnpm-lock.yaml package.json turbo.json tsconfig.base.json ./
COPY apps/web ./apps/web
COPY packages ./packages

# pnpm installs each workspace package's binaries into its own node_modules
# (e.g. apps/web/node_modules/.bin/next) as symlinks into the root .pnpm store.
# Copy that directory from deps so the symlinks resolve without re-running
# install (which would wipe and rebuild node_modules from scratch).
COPY --from=deps /repo/apps/web/node_modules ./apps/web/node_modules

# Next.js needs the API base URL baked in at build time for static analysis;
# the runtime NEXT_PUBLIC_API_URL can override it at container start.
ARG NEXT_PUBLIC_API_URL=https://api-staging.thepandit.app/v1
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NODE_ENV=production

RUN pnpm --filter @pandit/web run build

# ── Runtime ───────────────────────────────────────────────────────────────────
FROM node:20-alpine AS runtime

WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000

RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs

COPY --from=builder /repo/apps/web/public ./public
COPY --from=builder --chown=nextjs:nodejs /repo/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /repo/apps/web/.next/static ./.next/static

USER nextjs
EXPOSE 3000

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD wget -qO- http://localhost:3000/api/healthz || exit 1

CMD ["node", "server.js"]
