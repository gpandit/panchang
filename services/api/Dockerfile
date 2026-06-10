# ── Build stage ───────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

RUN pip install --no-cache-dir uv==0.5.26

# Copy workspace manifests first for layer-cache efficiency
COPY pyproject.toml uv.lock ./
COPY services/api/pyproject.toml ./services/api/
COPY services/panchang/pyproject.toml ./services/panchang/

# Install runtime deps for the api package into a prefix
# --no-install-workspace: install only third-party deps here; the local
# packages (api, panchang) run from PYTHONPATH at runtime, and their src/
# is copied below — so they must NOT be built at this step (source absent yet).
RUN uv sync --package the-pandit-api --no-dev --no-cache --no-install-workspace

# Copy source
COPY services/api/src ./services/api/src
COPY services/panchang/src ./services/panchang/src

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Swiss Ephemeris data directory (AGPL build — commercial licence is a hard launch gate)
ENV SWISSEPH_PATH=/opt/swisseph/ephe
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the virtualenv from builder
COPY --from=builder /build/.venv /app/.venv

# Copy application source
COPY --from=builder /build/services/api/src /app/services/api/src
COPY --from=builder /build/services/panchang/src /app/services/panchang/src

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/services/api/src:/app/services/panchang/src"

EXPOSE 8000

# Health probe endpoint is GET /healthz (defined in main.py)
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
