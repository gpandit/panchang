"""Cross-checks resolved festival dates against the curated reference Panchang
(extends Step 1.3's accuracy harness — `tools/accuracy_harness/data/
reference_festivals.json`), per the "Done when" criterion of Step 2.2:
major festivals must resolve to correct dates for a sample location/year,
verified against the reference Panchang.

This is the one place real Swiss-Ephemeris computation happens for this
module: each (date, location) pair is computed exactly once via the engine
and memoized, then every rule is matched against that single year-long scan —
mirroring how the cached Panchang is read in production (the engine is the
single source of truth; this module never recomputes it independently).
"""

from __future__ import annotations

import itertools
import json
from datetime import date
from pathlib import Path

import pytest
from festivals.recurring import RecurringKind, generate_year
from festivals.resolver import resolve_year
from festivals.rules import RULES_BY_ID

from panchang.compute import compute_panchang
from panchang.models import MonthScheme, PanchangRequest, PanchangResult

DATE_TOLERANCE_DAYS = 1  # see reference_festivals.json _meta.tolerance_policy

_FIXTURES_PATH = (
    Path(__file__).resolve().parents[3]
    / "tools"
    / "accuracy_harness"
    / "data"
    / "reference_festivals.json"
)


def _load_reference() -> dict:
    return json.loads(_FIXTURES_PATH.read_text())


@pytest.fixture(scope="module")
def reference() -> dict:
    return _load_reference()


@pytest.fixture(scope="module")
def memoized_source(reference):
    """Compute the whole reference year for the reference location exactly
    once via the real engine, then serve every subsequent lookup from memory —
    every rule resolves against this single scan."""
    loc = reference["location"]
    cache: dict[date, PanchangResult] = {}

    def source(d: date) -> PanchangResult:
        if d not in cache:
            cache[d] = compute_panchang(
                PanchangRequest(
                    date=d,
                    lat=loc["lat"],
                    lon=loc["lon"],
                    tz=loc["tz"],
                    month_scheme=MonthScheme(loc["month_scheme"]),
                )
            )
        return cache[d]

    return source


def test_major_festivals_resolve_within_tolerance(reference, memoized_source) -> None:
    year = reference["year"]
    mismatches = []

    for fixture in reference["fixtures"]:
        rule = RULES_BY_ID[fixture["rule_id"]]
        occurrences = resolve_year(rule, year, memoized_source)
        expected = date.fromisoformat(fixture["date"])

        assert occurrences, (
            f"{fixture['rule_id']}: rule did not resolve to any occurrence in {year}"
        )
        resolved = occurrences[0].date
        if abs((resolved - expected).days) > DATE_TOLERANCE_DAYS:
            mismatches.append(
                f"  {fixture['rule_id']} ({fixture['name']}): expected {expected}, resolved {resolved}"
            )

    assert not mismatches, "Festival resolution mismatches beyond tolerance:\n" + "\n".join(
        mismatches
    )


def test_resolution_is_deterministic_across_runs(reference, memoized_source) -> None:
    """A second resolution pass over the same (cached) Panchang must be
    byte-identical — the resolver must be a pure function of its inputs."""
    year = reference["year"]
    rule = RULES_BY_ID["diwali"]

    first = resolve_year(rule, year, memoized_source)
    second = resolve_year(rule, year, memoized_source)

    assert first == second


def test_recurring_observances_have_plausible_yearly_cadence(memoized_source, reference) -> None:
    """Each recurring observance must show up roughly the expected number of
    times across a year — the cadence assertion from the Step 2.2 spec."""
    year = reference["year"]

    ekadashis = generate_year(RecurringKind.EKADASHI, year, memoized_source)
    purnimas = generate_year(RecurringKind.PURNIMA, year, memoized_source)
    amavasyas = generate_year(RecurringKind.AMAVASYA, year, memoized_source)
    sankrantis = generate_year(RecurringKind.SANKRANTI, year, memoized_source)

    # ~2 Ekadashis/Purnimas/Amavasyas per lunar month (~12 lunar months/year);
    # exactly one Sankranti per solar-rashi transition (12/year).
    assert 22 <= len(ekadashis) <= 26
    assert 11 <= len(purnimas) <= 13
    assert 11 <= len(amavasyas) <= 13
    assert len(sankrantis) == 12

    # Cadence: Ekadashi recurs ~twice per synodic month (~13-16d apart, never
    # skips — both pakshas always present at some sunrise).
    for prev, cur in itertools.pairwise(ekadashis):
        gap = (cur.date - prev.date).days
        assert 10 <= gap <= 20, (
            f"Ekadashi: implausible gap {gap}d between {prev.date} and {cur.date}"
        )

    # Purnima/Amavasya each occur once per synodic month (~27-32d). Rarely a
    # cycle's Amavasya/Purnima tithi falls entirely between two sunrises (a
    # Kshaya tithi — Architecture §5 calls out respecting these labels) and
    # is genuinely absent from the headline-anga sequence for that month, so
    # an occasional doubled gap (~2 cycles, ~56-64d) is expected, not a bug.
    for occurrences, label in ((purnimas, "Purnima"), (amavasyas, "Amavasya")):
        for prev, cur in itertools.pairwise(occurrences):
            gap = (cur.date - prev.date).days
            assert (25 <= gap <= 33) or (56 <= gap <= 64), (
                f"{label}: implausible gap {gap}d between {prev.date} and {cur.date}"
            )

    for prev, cur in itertools.pairwise(sankrantis):
        gap = (cur.date - prev.date).days
        assert 25 <= gap <= 35, (
            f"Sankranti: implausible gap {gap}d between {prev.date} and {cur.date}"
        )
