# ── Build stage ───────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# pyswisseph has no prebuilt wheel for every platform; when it falls back to an
# sdist it needs a C toolchain to compile the Swiss Ephemeris extension.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.5.26

COPY pyproject.toml uv.lock ./
COPY services/panchang/pyproject.toml ./services/panchang/

# --no-install-workspace: install only third-party deps here; the local
# panchang package runs from PYTHONPATH at runtime and its src/ is copied
# below — so it must NOT be built at this step (source absent yet).
RUN uv sync --package the-pandit-panchang --no-dev --no-cache --no-install-workspace

COPY services/panchang/src ./services/panchang/src

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Swiss Ephemeris AGPL build — commercial licence is a hard launch gate for production.
ENV SWISSEPH_PATH=/opt/swisseph/ephe
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY --from=builder /build/.venv /app/.venv
COPY --from=builder /build/services/panchang/src /app/src

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

EXPOSE 8001

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')"

CMD ["uvicorn", "panchang.app:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
