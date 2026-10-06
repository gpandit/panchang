# ADR-0004: Enforce executable Panchang accuracy tolerances

- **Status:** Accepted
- **Date:** 2026-10-07
- **Decision area:** Panchang correctness and release gates

## Context

Published Panchangs can differ because of ephemeris builds, refraction and
horizon conventions, rounding, and rendering. The product nevertheless needs a
stable, executable contract that catches wrong locations, timezones, ayanamsa,
angle calculations, and labels. A ±1 minute aspiration is not evidence of
correctness by itself.

## Decision

The release contract is:

| Output | Required comparison |
|---|---|
| Sunrise and sunset | absolute difference no greater than ±2 minutes |
| Tithi, Nakshatra, Yoga, and Karana boundaries | absolute difference no greater than ±5 minutes |
| Anga names, Vara, and calendrical labels | exact equality |
| Adhika/Kshaya flags | exact equality |

The tolerance policy is executable in `tools/accuracy_harness/` and remains
aligned with `docs/architecture/accuracy-tolerances.md`. The ±1 minute value is
a stretch target, not a release claim. The harness covers the headline anga
boundaries; unit/property/edge-case tests cover full interval sequences,
monotonicity, DST, Adhika/Kshaya/Vriddhi, both month schemes, and marked
high-latitude sunrise fallback.

S1 is not complete until the independent reference set reaches at least 500
days across at least 10 locations and the executable harness is green. A
tolerance change requires new reference evidence, an explanation of the
external-source convention, and a superseding ADR; it may not be made merely
to make a failing implementation pass.

## Consequences

Accuracy is a merge and stage gate, not a manual review assertion. Some valid
source-convention differences must be documented, and fixture maintenance is
ongoing. The contract makes false precision visible while preserving strict
checks for names and labels.

## Verification and gates

- Run `uv run python tools/accuracy_harness/run.py` for every PCS change.
- Keep fixture source URL and fetch date with each reference.
- CI checks the fixture count/location coverage at the S1 gate and rejects
  unmarked synthetic fallback output.

## References

- `docs/architecture/accuracy-tolerances.md`
- `docs/architecture-v3.0.md`, §§4.1 and 8–9
- `docs/design-development-plan-v3.0.md`, §4
- `docs/requirements-v3.0.md`, §4.1
