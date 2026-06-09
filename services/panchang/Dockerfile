# ── Build stage ───────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

RUN pip install --no-cache-dir uv==0.5.26

COPY pyproject.toml uv.lock ./
COPY services/panchang/pyproject.toml ./services/panchang/

RUN uv sync --package the-pandit-panchang --no-dev --no-cache

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
