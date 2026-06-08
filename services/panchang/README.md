# services/panchang — Panchang Computation Service

The single source of astronomical truth for The Pandit platform.

Stack: Python 3.12 · FastAPI · pyswisseph (Swiss Ephemeris)

**This is the first service built (Stage 1, Steps 1.1–1.3).**
Everything else is downstream and trusts its output unconditionally.

## Engine parameters

| Parameter    | Value                                   |
|--------------|-----------------------------------------|
| Ephemeris    | Swiss Ephemeris (AGPL dev build)        |
| Ayanamsa     | Lahiri (Chitrapaksha) — configurable    |
| Day boundary | Sunrise-to-sunrise, per location        |
| Month scheme | Amanta & Purnimanta, user-selectable    |
| Methodology  | Drik Ganita (observational)             |

## ⚠️ Licence note

The free Swiss Ephemeris build (AGPL) is used for development and testing.
The **commercial licence is a hard gate before any public launch build.**
Do not ship to production without securing it.

## Running locally

```bash
cp .env.example .env
uv run uvicorn panchang.main:app --reload --port 8001
```

## Tests

```bash
uv run pytest tests/ -v
```

The accuracy harness (Step 1.3) validates computed Panchang values against
reference data and runs in CI, gating all merges.
