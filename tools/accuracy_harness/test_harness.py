"""Tests for the accuracy harness itself, and the green run over the curated
reference dataset (Step 1.3 — see docs/accuracy-tolerances.md for policy).

Run with:  pytest tools/accuracy_harness/test_harness.py
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

from panchang.compute import compute_panchang
from panchang.models import PanchangRequest

_TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from accuracy_harness.run import _load_fixtures, compare_fixture, run_fixture  # noqa: E402


def test_reference_dataset_passes() -> None:
    """Green run: every curated fixture must match the engine within tolerance."""
    fixtures = _load_fixtures()
    assert fixtures, "reference dataset must not be empty"

    all_mismatches = []
    for fixture in fixtures:
        all_mismatches.extend(run_fixture(fixture))

    assert not all_mismatches, "\n".join(m.render() for m in all_mismatches)


def test_meta_harness_catches_a_deliberately_wrong_value() -> None:
    """The harness must fail loudly when a fixture's expected value is wrong —
    otherwise a silently-broken comparison would let real regressions through."""
    fixtures = _load_fixtures()
    fixture = copy.deepcopy(fixtures[0])
    request = PanchangRequest(**fixture["request"])
    result = compute_panchang(request)

    # Sanity: the untouched fixture passes.
    assert compare_fixture(fixture, result) == []

    # Corrupt a name (exact-match field) and a boundary time (tolerance field).
    fixture["expected"]["tithi"]["name"] = "Definitely Not A Real Tithi"
    fixture["expected"]["sunrise"] = "1999-01-01T00:00:00"

    mismatches = compare_fixture(fixture, result)
    fields = {m.field for m in mismatches}

    assert "tithi.name" in fields, "wrong anga name must be caught"
    assert "sunrise" in fields, "wrong boundary time (beyond tolerance) must be caught"


def test_meta_harness_respects_tolerance_window() -> None:
    """A value within the documented tolerance must NOT be flagged — otherwise
    the harness would be too strict and fail on harmless source/engine drift."""
    fixtures = _load_fixtures()
    fixture = copy.deepcopy(fixtures[0])
    request = PanchangRequest(**fixture["request"])
    result = compute_panchang(request)

    from datetime import datetime, timedelta

    # Nudge the expected value by one minute — well inside the documented
    # ±2-minute sunrise/sunset tolerance — and confirm it still passes.
    actual_local = datetime.fromisoformat(result.day_events.sunrise.iso).replace(tzinfo=None)
    nudged = actual_local + timedelta(minutes=1)
    fixture["expected"]["sunrise"] = nudged.isoformat()

    mismatches = compare_fixture(fixture, result)
    assert not any(m.field == "sunrise" for m in mismatches)
