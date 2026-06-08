# services/api — API Gateway

Versioned REST/JSON gateway for The Pandit platform.

Stack: Python 3.12 · FastAPI

Clients (web, iOS, Android) call this service exclusively.
Domain services (`services/panchang`, etc.) are never exposed directly to clients.

## Running locally

```bash
cp .env.example .env
# Ensure docker-compose infra is up: docker compose -f infra/docker-compose.yml up -d
uv run uvicorn api.main:app --reload --port 8000

# Docs (debug mode only)
open http://localhost:8000/docs
```

## Tests

```bash
uv run pytest tests/ -v
```
