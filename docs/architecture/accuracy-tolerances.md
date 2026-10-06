# Panchang accuracy harness — tolerance policy

This document is the **committed contract** for the accuracy harness
(`tools/accuracy_harness/`). It defines, per field, how close the engine's
output must be to the curated reference values before the harness reports a
regression. It is read by `tools/accuracy_harness/run.py` (the comparison
runner is parameterised against the numbers below — keep them in sync).

The harness compares against values transcribed from an established published
Panchang (drikpanchang.com, Drik Ganita method, Lahiri ayanamsa — see
`source_url` on each fixture in `data/reference_panchang.json`). Published
Panchangs differ from the engine, and from each other, in small ways: rounding
to the nearest minute, slightly different ephemeris builds, and rendering
choices. The tolerances below absorb those differences without masking a real
regression.

## What is compared

For each fixture, the harness checks:

1. **Day events** — `sunrise`, `sunset` (local clock time).
2. **The headline anga per category** — the Tithi, Nakshatra, Yoga and Karana
   that are *active at the moment the Panchang day opens (sunrise)*. This is
   the anga a published Panchang headlines for the day, and the one most
   commonly consumed downstream (festival/vrat resolution, calendar cells).
   Each is checked as a `(name, end-boundary time)` pair.
3. **Vara** (weekday) — name only (it does not carry a boundary time).
4. **Calendrical labels**, where present in a fixture — `lunar_month`,
   `is_adhika_month`, `is_kshaya_month`.

Spans beyond the headline anga (i.e. what the day transitions *into*) are
intentionally out of scope for this harness — they are exercised by the unit
suite (`services/panchang/tests/test_compute.py`,
`services/panchang/tests/test_edge_cases.py`), which can assert on the full
`AngaSpan` sequence directly without needing an external reference value for
every transition.

## Tolerances per field

| Field                                   | Comparison            | Tolerance        |
|-----------------------------------------|-----------------------|------------------|
| `sunrise`, `sunset`                      | absolute time diff    | **± 2 minutes**  |
| Anga boundary times (Tithi/Nakshatra/Yoga/Karana `end`) | absolute time diff | **± 5 minutes** |
| Anga / Vara / month **names and labels** | string equality       | **exact** (no tolerance) |
| `is_adhika_month`, `is_kshaya_month`     | boolean equality      | **exact**        |

**Why these numbers.**

- *± 2 minutes for sunrise/sunset*: published Panchangs round rise/set times
  to the nearest minute and may use a slightly different refraction/horizon
  convention; the engine uses `swe.rise_trans` with standard atmospheric
  refraction. Two minutes comfortably absorbs that without hiding a wrong
  ephemeris/location/timezone.
- *± 5 minutes for anga boundaries*: anga boundaries are found by bisecting a
  fast-moving angle (the Moon moves ~0.5°/hour relative to the Sun for Tithi,
  faster still for Nakshatra/Karana). A few minutes of drift between
  ephemeris builds, or in how a published source rounds/truncates its
  underlying computation, is expected and harmless; five minutes is tight
  enough that a genuine bug (wrong anga, wrong day, swapped Sun/Moon, wrong
  ayanamsa) will still fail loudly.
- *Names/labels are exact*: there is no excuse for a spelling or sequence
  mismatch — these come from static tables (`panchang.constants`) and a
  mismatch means the wrong index was computed, which is exactly the class of
  bug this harness exists to catch.

## Extending the dataset

Add a new fixture object to the `fixtures` array in
`data/reference_panchang.json`:

```jsonc
{
  "id": "kebab-case-unique-id",
  "label": "Human-readable description (location, scheme, why it matters)",
  "source_url": "https://... (the page you transcribed values from)",
  "fetched": "YYYY-MM-DD",
  "request": { "date": "YYYY-MM-DD", "lat": ..., "lon": ..., "tz": "IANA/Zone",
               "ayanamsa": "lahiri", "month_scheme": "amanta" | "purnimanta" },
  "expected": {
    "sunrise": "YYYY-MM-DDTHH:MM:SS", "sunset": "YYYY-MM-DDTHH:MM:SS",
    "vara": "...",
    "tithi":     { "name": "...", "end": "YYYY-MM-DDTHH:MM:SS" },
    "nakshatra": { "name": "...", "end": "YYYY-MM-DDTHH:MM:SS" },
    "yoga":      { "name": "...", "end": "YYYY-MM-DDTHH:MM:SS" },
    "karana":    { "name": "...", "end": "YYYY-MM-DDTHH:MM:SS" },
    "lunar_month": "... (optional)",
    "is_adhika_month": true|false, "is_kshaya_month": true|false   // optional
  }
}
```

Notes for transcription:

- `expected.*.end` is the **local** boundary instant in the location's `tz`,
  written as a bare ISO datetime (no offset) — it may roll onto the following
  civil date (e.g. `02:16` after midnight is still written with the next
  day's date). The harness compares it against the engine's `TimeValue.iso`.
- Normalize Vara/anga spellings to the engine's canonical transliteration in
  `panchang.constants` (e.g. `Somavara`, not `Somawara`) — this is a spelling
  normalization of the transcription, not a change to the reference value.
- Always record `source_url` and `fetched` so a future contributor can
  re-derive or re-verify the value.

Run the harness locally with:

```sh
uv run python tools/accuracy_harness/run.py
```
