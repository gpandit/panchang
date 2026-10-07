# Panchang engine — lunar edge cases

Step 1.2 makes the engine correct on the hard days listed in Architecture
§4.2 "Lunar edge cases the build must handle". This document records, for
each case, the rationale and the reference behaviour the engine guarantees
and the test suite (`tests/test_edge_cases.py`) asserts.

---

## 1. Adhika & Kshaya maas (leap / skipped lunar months)

**Rule.** A (Amanta) lunar month runs new-moon to new-moon. Whether it is
ordinary, Adhika (leap) or Kshaya (skipped) is determined by how many times
the Sun crosses into a new sidereal rashi (a *sankranti*) between the two
bounding new moons:

| Sankrantis between new moons | Label                                   |
|-------------------------------|-----------------------------------------|
| exactly 1                     | ordinary month                           |
| 0 (Sun stays in the same rashi) | **Adhika** (leap) — the month repeats   |
| 2 (Sun crosses twice)         | **Kshaya** (skipped, very rare)          |

**Implementation** (`compute._detect_adhika_kshaya`): the bounding new moons
are located by bisecting the tithi angle (Moon − Sun) to 0° within a ±2-day
window around a mean-tithi-length estimate of where each one should fall
(`_SYNODIC_MONTH / 30` per tithi). The Sun's sidereal rashi at each new moon
is then compared; `diff = (rashi_next − rashi_prev) mod 12` gives the count
above (0 → Adhika, 2 → Kshaya, else ordinary).

**Calibration caveat.** The ±2-day bisection window is placed using a mean
synodic month (~29.53 days), not an independently verified new-moon bracket.
When the crossing is not found, the implementation silently uses the estimate;
the resulting Adhika/Kshaya label may be wrong. The root-finder's 80 iterations
do not prove that the search window contains the intended crossing. Independent
fixtures, including rare Kshaya months, are still needed for the v3.0 accuracy
gate.

**Surfaced as.** `Calendrical.is_adhika_month` / `Calendrical.is_kshaya_month`
— booleans on every result, so downstream festival resolution (Stage 1,
later steps) can apply Adhika/Kshaya-specific rules without recomputing
astronomy.

**Reference behaviour tested.** 2023 carried a well-documented Adhika
Shravan (~18 Jul – 16 Aug 2023, "Purushottam Maas"); a date inside that
window (2023-08-01) must report `is_adhika_month = True`,
`is_kshaya_month = False`. An ordinary month (2024-01-15) must report both
flags `False`.

Genuine Kshaya maas occurrences are astronomically rare — gaps of decades
between them — so rather than search the calendar for one, the test exercises
`_detect_adhika_kshaya` directly against a synthetic double-sankranti month,
verifying the `diff == 2 → Kshaya` / `diff == 0 → Adhika` branches of the
rule in isolation.

---

## 2. Kshaya & Vriddhi tithis

**Rule.** Because a tithi (~12° of Moon-minus-Sun motion, ~23h37m on
average) is slightly shorter than a solar day, occasionally:

- a **Kshaya tithi** begins *and* ends between two sunrises — it never
  "owns" a sunrise and so never appears as *the* tithi of any Panchang day
  on its own;
- a **Vriddhi tithi** is long enough to still be running at the *next*
  sunrise too — it is the governing tithi of two consecutive Panchang days.

**Representation.** No special-casing is needed in the engine's span model —
`AngaSpan` already represents both unambiguously by construction:

- **Kshaya**: the affected day's `tithi` list has **three** entries instead
  of the usual one or two. The middle entry has *both* `start` and `end`
  populated (it is wholly contained within the Panchang day — clipped on
  neither side), unlike a normal boundary-crossing tithi whose `start` or
  `end` is `None`.
- **Vriddhi**: the tithi appears as the **last** entry of one day's `tithi`
  list with `end = None` (still running at the next sunrise) *and* as the
  **first** entry of the following day's list with `start = None` (already
  running at this sunrise) — same `index` and `name` in both, so the
  continuity is explicit and lossless.

**Reference behaviour tested.**
- Kshaya: 2024-01-14 (Asia/Kolkata, Delhi) — `Shukla Chaturthi` is fully
  contained between `Shukla Tritiya` and `Shukla Panchami`, with exact
  boundary chaining (no gap/overlap).
- Vriddhi: 2024-01-12 → 2024-01-13 (same location) — `Shukla Dwitiya` is the
  open-ended last tithi of the first day and the start-less first tithi of
  the second, same index and name.

---

## 3. High-latitude / undefined sunrise (polar regions)

**Problem.** Above the polar circles, during polar day or polar night, the
Sun does not cross the horizon on a given civil date — `rise_trans` returns
`None` for sunrise and/or sunset, so no genuine sunrise-to-sunrise span
exists to anchor the Panchang day.

**Named policy: `sunriseFallbackNearestValidLatitude`.** First search for a
sunrise on the requested local date at the actual coordinates, with a sunset
later **on that date**, then the next sunrise on the following local date.
When that triplet cannot be established, move towards the equator at the same
longitude in deterministic 1° latitude steps (plus 0°), keeping the original
IANA timezone and requested date. The first candidate with all three events
in the correct local-day order supplies the proxy sunrise, sunset, and next
sunrise. Search is bounded by 91 candidate latitudes. The reference latitude
is deliberately not interpreted as the location of the requester; these are
**approximate anchors**, not observed sunrise/sunset at the original site.
The choice of 1° resolution is a reproducibility policy, not an accuracy
claim. This policy does not substitute events from another civil date and
does not carry forward a weeks-old polar sunrise. Sunrise-relative angas,
muhurat, choghadiya and hora are therefore approximate too.

**Flags and failure.** Successful proxy results carry `sunriseFallback` and
`sunriseFallbackNearestValidLatitude` in the result and day-event flags, and
`sunriseFallback` on every canonical interval. At ≥66° latitude, the
seasonal sign of solar declination additionally supplies `polarDay` or
`polarNight`; this is an approximate seasonal classification, not measured
local daylight. The Today view withholds rise/set when `sunriseFallback` is
present, rather than calling a proxy time observed. Event timestamps and
interval endpoints still denote real **UTC instants**, with local offsets
computed independently across DST. Moonrise/moonset are still searched at
the original coordinates within the resulting window.

If the local date (including the following civil date) has no representable
midnight, or is out of range, computation fails with
`SunriseFallbackError(reason="impossibleLocalDate")`. If no inward latitude
produces a valid triplet, it fails with reason `noValidLatitude`; no bogus
Panchang is returned. The PCS `/compute` endpoint responds with HTTP 422 and
`{"reason": ..., "flags": ["sunriseFallback", "sunriseFallbackUnavailable", reason]}`.
For example, Samoa's skipped local date 2011-12-30 is rejected. The daily
gateway propagates that structured failure as HTTP 422 `detail`, rather than
relabelling it as a computed day; the existing monthly gateway skips failed
dates in its partial-result response (it does not emit false day entries).
PCS and gateway in-process cache namespaces were advanced to v3 for this
policy. External CDN entries keyed only by URL must still expire (or be
purged) at deployment; the current daily edge TTL is one hour.

**Reference behaviour tested.** Longyearbyen (78.2°N), June/December 2024,
Southern polar dates and DST-boundary dates: triplet order, local-day identity,
UTC interval identity, approximation flags and explicit failure paths.

---

## 4. DST transitions occurring mid-tithi

**Problem.** A tithi (or any anga) can be running while the local civil
clock springs forward (loses an hour) or falls back (repeats an hour). The
24-plus ("past-midnight") display form must keep reading monotonically
across such a transition — it must not jump backwards, repeat a value, or
skip an hour purely because the civil clock did.

**Why the implementation gets this right.** `timeforms.to_time_value`
converts both the event and local civil midnight to UTC before subtracting;
subtracting two datetimes with the **same IANA timezone object** would instead
use wall-clock arithmetic across DST. The UTC difference is **elapsed real
time**, not wall-clock arithmetic. A spring-forward
("2:00 → 3:00" never occurs on the wall clock, but one hour of real time
still passes) and a fall-back (the wall clock reads "1:30" twice, 3600
real seconds apart) both produce a strictly increasing `hour_24_plus`
sequence, because the underlying subtraction is offset-aware.

**Decision recorded.** `hour_24_plus` is defined as *elapsed real seconds
since the Panchang day's civil midnight*, rendered as `HH:MM:SS` — not as a
wall-clock relabelling. This is the only definition that stays internally
consistent (strictly increasing, no duplicate/skipped readings) across a DST
boundary, which is what downstream consumers (Tithi-based reminders,
muhurat windows) need: a reliable ordering and duration arithmetic.

**Reference behaviour tested.** America/New_York on 2024-03-10 (spring
forward, 02:00 → 03:00 skipped) and 2024-11-03 (fall back, 01:00–02:00
repeated): the engine computes without error, and every anga boundary's
`hour_24_plus` value — across all tithi/nakshatra/yoga/karana spans for the
day — is non-decreasing when read in chronological order.
