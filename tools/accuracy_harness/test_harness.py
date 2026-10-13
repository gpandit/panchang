"""Tests for the accuracy harness itself, and the green run over the curated
reference dataset (Step 1.3 — see docs/accuracy-tolerances.md for policy).

Run with:  pytest tools/accuracy_harness/test_harness.py
"""

from __future__ import annotations

import copy
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from panchang.compute import compute_panchang
from panchang.models import PanchangRequest

_TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from accuracy_harness.run import (  # noqa: E402
    _check_time,
    _load_fixtures,
    _reference_instant,
    compare_fixture,
    gate_gaps,
    run_fixture,
    validate_dataset,
)


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


def test_dataset_validation_requires_reproducible_provenance() -> None:
    """A local/generated table must not silently become an accuracy reference."""
    fixtures = copy.deepcopy(_load_fixtures())
    fixtures[0]["source_url"] = "file:///tmp/reference.json"

    try:
        validate_dataset(fixtures)
    except ValueError as exc:
        assert "source_url" in str(exc)
    else:
        raise AssertionError("non-HTTPS reference provenance must be rejected")


def test_gate_report_does_not_count_timezone_supplement_as_accuracy_days() -> None:
    """The ten-record conversion supplement is not an independent day dataset."""
    payload = json.loads(
        (Path(__file__).parent / "data" / "timezone_conversion_20261007.json").read_text()
    )
    assert len(payload["records"]) == 10
    assert "not an independent 500-day accuracy dataset" in payload["_meta"]["accuracy_gate"]
    gaps = gate_gaps(_load_fixtures())
    assert "days 4/500" in gaps
    assert "locations 3/10" in gaps


def test_rise_set_and_anga_thresholds_and_dst_instants() -> None:
    tz = ZoneInfo("America/New_York")
    expected = "2024-11-03T01:30:00-04:00"
    assert _check_time("dst", "sunrise", expected, "2024-11-03T01:32:00-04:00", 2, tz) is None
    assert _check_time("dst", "tithi.end", expected, "2024-11-03T01:35:00-04:00", 5, tz) is None
    assert _check_time("dst", "sunrise", expected, "2024-11-03T01:32:01-04:00", 2, tz)
    assert _check_time("dst", "tithi.end", expected, "2024-11-03T01:35:01-04:00", 5, tz)
    # Identical wall time in a DST fold is an hour apart in absolute time.
    assert _check_time("dst", "tithi.end", expected, "2024-11-03T01:30:00-05:00", 5, tz)
    with pytest.raises(ValueError, match="ambiguous"):
        _reference_instant("2024-11-03T01:30:00", tz)
    with pytest.raises(ValueError, match="nonexistent"):
        _reference_instant("2024-03-10T02:30:00", tz)


def test_all_anga_names_and_boundaries_are_required_and_checked() -> None:
    fixture = copy.deepcopy(_load_fixtures()[0])
    fixture["expected"].pop("yoga")
    with pytest.raises(KeyError):
        validate_dataset([fixture])
    fixture = copy.deepcopy(_load_fixtures()[0])
    result = compute_panchang(PanchangRequest(**fixture["request"]))
    for field in ("tithi", "nakshatra", "yoga", "karana"):
        altered = copy.deepcopy(fixture)
        actual = getattr(result, field)[0].end
        assert actual is not None
        altered["expected"][field]["end"] = (
            datetime.fromisoformat(actual.iso).replace(tzinfo=None) + timedelta(minutes=6)
        ).isoformat()
        assert any(m.field == f"{field}.end" for m in compare_fixture(altered, result))
