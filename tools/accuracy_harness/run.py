#!/usr/bin/env python3
"""Panchang accuracy harness — comparison runner.

Computes the engine's output for every fixture in
`data/reference_panchang.json` and asserts it matches the curated reference
values within the tolerances documented in `docs/accuracy-tolerances.md`
(the single source of truth for the numbers below — keep them in sync).

Exit codes:
  0 — every fixture matched within tolerance
  1 — at least one mismatch (a clear expected/actual diff is printed)

Run with:  uv run python tools/accuracy_harness/run.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

# Make the panchang package importable when run as a plain script (mirrors
# tools/check_launch_readiness.py's "no package" approach).
_SERVICE_SRC = Path(__file__).resolve().parents[2] / "services" / "panchang" / "src"
if str(_SERVICE_SRC) not in sys.path:
    sys.path.insert(0, str(_SERVICE_SRC))

from panchang.compute import compute_panchang  # noqa: E402
from panchang.models import AngaSpan, PanchangRequest, PanchangResult  # noqa: E402

DATA_PATH = Path(__file__).parent / "data" / "reference_panchang.json"

# ─── Tolerance policy (docs/accuracy-tolerances.md is the committed source) ──
SUNRISE_SUNSET_TOLERANCE_MINUTES = 2
ANGA_BOUNDARY_TOLERANCE_MINUTES = 5

_ANGA_FIELDS = ("tithi", "nakshatra", "yoga", "karana")


@dataclass
class Mismatch:
    fixture_id: str
    field: str
    expected: Any
    actual: Any
    detail: str = ""

    def render(self) -> str:
        line = (
            f"  [{self.fixture_id}] {self.field}: expected={self.expected!r} actual={self.actual!r}"
        )
        if self.detail:
            line += f"  ({self.detail})"
        return line


def _load_fixtures() -> list[dict[str, Any]]:
    raw = json.loads(DATA_PATH.read_text())
    return list(raw["fixtures"])


def _parse_local(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _check_time(
    fixture_id: str, field: str, expected_iso: str, actual_iso: str, tolerance_minutes: int
) -> Mismatch | None:
    expected_dt = _parse_local(expected_iso)
    actual_dt = _parse_local(actual_iso).replace(tzinfo=None)
    diff_minutes = abs((actual_dt - expected_dt).total_seconds()) / 60.0
    if diff_minutes > tolerance_minutes:
        return Mismatch(
            fixture_id,
            field,
            expected_iso,
            actual_iso,
            detail=f"off by {diff_minutes:.1f} min, tolerance is ±{tolerance_minutes} min",
        )
    return None


def _check_exact(fixture_id: str, field: str, expected: Any, actual: Any) -> Mismatch | None:
    if expected != actual:
        return Mismatch(fixture_id, field, expected, actual)
    return None


def _headline_span(spans: list[AngaSpan]) -> AngaSpan:
    """The anga active when the Panchang day opens — the first span (it always
    overlaps sunrise; `compute_panchang` enumerates spans from day_start)."""
    return spans[0]


def compare_fixture(fixture: dict[str, Any], result: PanchangResult) -> list[Mismatch]:
    """Return every mismatch between `fixture["expected"]` and `result`."""
    fid = fixture["id"]
    expected = fixture["expected"]
    mismatches: list[Mismatch] = []

    def add(m: Mismatch | None) -> None:
        if m is not None:
            mismatches.append(m)

    add(
        _check_time(
            fid,
            "sunrise",
            expected["sunrise"],
            result.day_events.sunrise.iso,
            SUNRISE_SUNSET_TOLERANCE_MINUTES,
        )
    )
    add(
        _check_time(
            fid,
            "sunset",
            expected["sunset"],
            result.day_events.sunset.iso,
            SUNRISE_SUNSET_TOLERANCE_MINUTES,
        )
    )
    add(_check_exact(fid, "vara.name", expected["vara"], result.vara.name))

    spans_by_field = {
        "tithi": result.tithi,
        "nakshatra": result.nakshatra,
        "yoga": result.yoga,
        "karana": result.karana,
    }
    for field in _ANGA_FIELDS:
        if field not in expected:
            continue
        exp = expected[field]
        headline = _headline_span(spans_by_field[field])
        add(_check_exact(fid, f"{field}.name", exp["name"], headline.name))
        if headline.end is None:
            mismatches.append(
                Mismatch(
                    fid,
                    f"{field}.end",
                    exp["end"],
                    None,
                    detail="engine span has no end boundary within the Panchang day",
                )
            )
        else:
            add(
                _check_time(
                    fid,
                    f"{field}.end",
                    exp["end"],
                    headline.end.iso,
                    ANGA_BOUNDARY_TOLERANCE_MINUTES,
                )
            )

    if "lunar_month" in expected:
        add(
            _check_exact(
                fid,
                "calendrical.lunar_month",
                expected["lunar_month"],
                result.calendrical.lunar_month,
            )
        )
    if "is_adhika_month" in expected:
        add(
            _check_exact(
                fid,
                "calendrical.is_adhika_month",
                expected["is_adhika_month"],
                result.calendrical.is_adhika_month,
            )
        )
    if "is_kshaya_month" in expected:
        add(
            _check_exact(
                fid,
                "calendrical.is_kshaya_month",
                expected["is_kshaya_month"],
                result.calendrical.is_kshaya_month,
            )
        )

    return mismatches


def run_fixture(fixture: dict[str, Any]) -> list[Mismatch]:
    request = PanchangRequest(**fixture["request"])
    result = compute_panchang(request)
    return compare_fixture(fixture, result)


def main() -> int:
    fixtures = _load_fixtures()
    total_mismatches: list[Mismatch] = []

    for fixture in fixtures:
        mismatches = run_fixture(fixture)
        status = "PASS" if not mismatches else "FAIL"
        print(f"[{status}] {fixture['id']} — {fixture.get('label', '')}")
        total_mismatches.extend(mismatches)

    if total_mismatches:
        print(f"\n{len(total_mismatches)} mismatch(es) found:\n")
        for m in total_mismatches:
            print(m.render())
        print(
            "\nSee docs/accuracy-tolerances.md for the tolerance policy and "
            "data/reference_panchang.json (`source_url`) for how to re-derive "
            "the reference values."
        )
        return 1

    print(f"\nAll {len(fixtures)} fixture(s) passed within tolerance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
