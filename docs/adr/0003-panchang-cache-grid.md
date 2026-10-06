# ADR-0003: Use a configurable 0.1° Panchang cache grid

- **Status:** Accepted
- **Date:** 2026-10-07
- **Decision area:** PCS cache and location normalization

## Context

Panchang computation is deterministic but expensive and must be shared by web,
mobile, reminders, festivals, and planners. Exact coordinates would fragment
the cache, while a location grid needs to preserve timezone and astronomical
correctness. The v3.0 documents name a configurable 0.1° default and require
engine-versioned invalidation.

## Decision

Normalize latitude and longitude to a configured 0.1° grid by a single,
documented rounding policy and use the normalized decimal values in every cache
key. The canonical key is:

```text
panchang:{date}:{grid_lat}:{grid_lon}:{iana_tz}:{ayanamsa}:{month_scheme}:{engine_version}
```

The key must preserve the IANA timezone, ayanamsa, month scheme, and computation
engine version. PostgreSQL is the durable canonical cache; Redis is the fast
lookup and coordination layer. A miss takes a per-key distributed lock, computes
through PCS, validates the result, and writes only the validated payload.

Entries are not silently expired. An engine or contract change creates a new
version/key and an explicit invalidation or backfill plan. Published festival
rule corrections invalidate dependent occurrence/cache material through their
versioned contract. The grid may be tightened or changed only with accuracy
evidence and a superseding ADR; the API still accepts the user's exact
coordinates for normalization and display context.

## Consequences

Most nearby requests share work, and all clients see one canonical result. A
grid introduces bounded spatial approximation, so the accuracy harness and
high-latitude fallback flags are release requirements. Redis loss is recoverable
from PostgreSQL or recomputation; Redis is never authoritative for user, money,
booking, or cache durability.

## Verification and gates

- Unit tests cover rounding boundaries, negative coordinates, key stability,
  timezone/scheme separation, engine-version separation, lock contention, and
  validated-write behavior.
- S1 warms at least 15 months for popular locations and measures cached-day p95
  at or below two seconds.
- Accuracy evidence is reviewed before changing grid resolution or fallback
  behavior.

## References

- `docs/architecture-v3.0.md`, §§4.1, 6, and 8
- `docs/design-development-plan-v3.0.md`, §§3 and 4
- `docs/requirements-v3.0.md`, §4.1
