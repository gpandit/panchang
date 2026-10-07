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

## S1-01 ephemeris boundary and calibration status

`src/panchang/engine.py` is the only module permitted to import/call Swiss
Ephemeris. `compute.py` uses named solar/lunar longitude and rise/set operations;
`timeforms.py` uses the engine's Julian Day conversion. The offline source guard
(`tools/check_contract_authority.py`) enforces the single-module import boundary.
This isolates the library; it does **not** establish calendrical accuracy.

Known gaps remain in `compute.py`: the mean-synodic-month estimate and ±2-day
search for bounding new moons may degrade to estimated instants when roots are
not found; lunar-month naming and Adhika/Kshaya labels need independent reference
calibration; Shaka/Vikram/Gujarati year changes use an approximate Gregorian
March 22 cutoff; and the polar sunrise/sunset placeholders are synthetic and
not yet flagged in the public response (the fixed 24-hour fallback also needs
DST-transition review). See `docs/edge-cases.md` for the current
fallback behavior. The current four-fixture accuracy harness passing is **not**
the v3.0 S1 exit gate (≥500 independently sourced days, ≥10 locations, ±2-minute
rise/set, ±5-minute anga boundaries, exact names/labels). No production accuracy
or commercial licensing approval is implied.
