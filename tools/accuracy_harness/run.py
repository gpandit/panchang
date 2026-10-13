#!/usr/bin/env python3
"""Panchang accuracy harness — comparison runner.

Computes the engine's output for every fixture in
`data/reference_panchang.json` and asserts it matches the curated reference
values within the tolerances documented in `docs/architecture/accuracy-tolerances.md`
(the single source of truth for the numbers below — keep them in sync).

Exit codes:
  0 — every fixture matched within tolerance (regression mode)
  1 — mismatch, invalid dataset, or unmet gate with --require-gate

Run with:  uv run python tools/accuracy_harness/run.py
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# Make the panchang package importable when run as a plain script (mirrors
# tools/check_launch_readiness.py's "no package" approach).
_SERVICE_SRC = Path(__file__).resolve().parents[2] / "services" / "panchang" / "src"
if str(_SERVICE_SRC) not in sys.path:
    sys.path.insert(0, str(_SERVICE_SRC))

from panchang.compute import compute_panchang  # noqa: E402
from panchang.models import AngaSpan, PanchangRequest, PanchangResult  # noqa: E402

DATA_PATH = Path(__file__).parent / "data" / "reference_panchang.json"

# ─── Tolerance policy (docs/architecture/accuracy-tolerances.md) ──
SUNRISE_SUNSET_TOLERANCE_MINUTES = 2
ANGA_BOUNDARY_TOLERANCE_MINUTES = 5
MIN_REFERENCE_DAYS = 500
MIN_LOCATIONS = 10

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


def _load_fixtures(path: Path = DATA_PATH) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text())
    fixtures = raw["fixtures"]
    validate_dataset(fixtures)
    return fixtures


def _reference_instant(value: str, tz: ZoneInfo) -> datetime:
    """Resolve a published local time; ambiguous/nonexistent wall times need an offset."""
    wall = datetime.fromisoformat(value)
    if wall.tzinfo is not None:
        instant = wall.astimezone(tz)
        if instant.replace(tzinfo=None) != wall.replace(tzinfo=None):
            raise ValueError(f"{value}: offset disagrees with IANA timezone {tz.key}")
        return instant
    candidates = [wall.replace(tzinfo=tz, fold=fold) for fold in (0, 1)]
    valid = [
        candidate
        for candidate in candidates
        if candidate.astimezone(UTC).astimezone(tz).replace(tzinfo=None) == wall
    ]
    if not valid or (len(valid) == 2 and valid[0].utcoffset() != valid[1].utcoffset()):
        raise ValueError(f"{value}: nonexistent or ambiguous local time; provide a UTC offset")
    return valid[0]


def validate_dataset(fixtures: list[dict[str, Any]]) -> None:
    """Reject incomplete, duplicated or untraceable references before any comparison."""
    if not fixtures:
        raise ValueError("independent reference dataset is empty")
    ids: set[str] = set()
    keys: set[tuple[date, float, float, str, str]] = set()
    for fixture in fixtures:
        fid = fixture["id"]
        if not isinstance(fid, str) or not fid.strip() or fid in ids:
            raise ValueError(f"duplicate or empty fixture id: {fid!r}")
        ids.add(fid)
        source = urlparse(fixture["source_url"])
        if source.scheme != "https" or not source.netloc:
            raise ValueError(f"{fid}: source_url must be a reproducible HTTPS citation")
        date.fromisoformat(fixture["fetched"])
        request = PanchangRequest(**fixture["request"])
        try:
            tz = ZoneInfo(request.tz)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"{fid}: unknown IANA timezone {request.tz}") from exc
        if not (-90 <= request.lat <= 90 and -180 <= request.lon <= 180):
            raise ValueError(f"{fid}: invalid coordinates")
        key = (request.date, request.lat, request.lon, request.tz, request.month_scheme.value)
        if key in keys:
            raise ValueError(f"{fid}: duplicate date/location/scheme reference")
        keys.add(key)
        exp = fixture["expected"]
        for field in ("sunrise", "sunset"):
            _reference_instant(exp[field], tz)
        if not isinstance(exp["vara"], str) or not exp["vara"]:
            raise ValueError(f"{fid}: missing vara name")
        for field in _ANGA_FIELDS:
            if not isinstance(exp[field]["name"], str) or not exp[field]["name"]:
                raise ValueError(f"{fid}: missing {field} name")
            _reference_instant(exp[field]["end"], tz)
        for field in ("is_adhika_month", "is_kshaya_month"):
            if field in exp and not isinstance(exp[field], bool):
                raise ValueError(f"{fid}: {field} must be boolean")
        if "tithi_flags" in exp and (
            not isinstance(exp["tithi_flags"], list)
            or any(flag not in {"kshaya", "vriddhi"} for flag in exp["tithi_flags"])
        ):
            raise ValueError(f"{fid}: tithi_flags must contain only kshaya/vriddhi")
        if "sunrise_fallback" in exp and not isinstance(exp["sunrise_fallback"], bool):
            raise ValueError(f"{fid}: sunrise_fallback must be boolean")


def gate_gaps(fixtures: list[dict[str, Any]]) -> list[str]:
    """Coverage is based on independently cited values, never generated engine output."""
    days = {f["request"]["date"] for f in fixtures}
    locations = {(f["request"]["lat"], f["request"]["lon"], f["request"]["tz"]) for f in fixtures}
    gaps = []
    if len(days) < MIN_REFERENCE_DAYS:
        gaps.append(f"days {len(days)}/{MIN_REFERENCE_DAYS}")
    if len(locations) < MIN_LOCATIONS:
        gaps.append(f"locations {len(locations)}/{MIN_LOCATIONS}")
    schemes = {f["request"]["month_scheme"] for f in fixtures if "lunar_month" in f["expected"]}
    for scheme in ("amanta", "purnimanta"):
        if scheme not in schemes:
            gaps.append(f"{scheme} month label")
    if not any(f["expected"].get("is_adhika_month") is True for f in fixtures):
        gaps.append("Adhika month")
    if not any(f["expected"].get("is_kshaya_month") is True for f in fixtures):
        gaps.append("Kshaya month")
    for flag in ("kshaya", "vriddhi"):
        if not any(flag in f["expected"].get("tithi_flags", []) for f in fixtures):
            gaps.append(f"{flag} tithi")
    if not any(abs(f["request"]["lat"]) >= 60 for f in fixtures):
        gaps.append("polar-edge location (>=60° latitude)")
    if not any(_crosses_dst(f) for f in fixtures):
        gaps.append("DST transition day")
    # PCS results contain no resolved festival occurrences yet; a label alone
    # cannot prove festival accuracy without comparing the resolver's output.
    gaps.append("major festival comparison (not supported by this harness yet)")
    return gaps


def _crosses_dst(fixture: dict[str, Any]) -> bool:
    request = fixture["request"]
    tz = ZoneInfo(request["tz"])
    day = date.fromisoformat(request["date"])
    before = datetime.combine(day, datetime.min.time(), tzinfo=tz).utcoffset()
    after = datetime.combine(day + timedelta(days=1), datetime.min.time(), tzinfo=tz).utcoffset()
    return before != after


def _check_time(
    fixture_id: str,
    field: str,
    expected_iso: str,
    actual_iso: str,
    tolerance_minutes: int,
    tz: ZoneInfo,
) -> Mismatch | None:
    expected_dt = _reference_instant(expected_iso, tz)
    actual_dt = datetime.fromisoformat(actual_iso)
    if actual_dt.tzinfo is None:
        return Mismatch(fixture_id, field, expected_iso, actual_iso, "engine time lacks UTC offset")
    # UTC arithmetic, including DST folds; wall-clock subtraction can hide an hour's drift.
    expected_dt = expected_dt.astimezone(UTC)
    actual_dt = actual_dt.astimezone(UTC)
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
    tz = ZoneInfo(fixture["request"]["tz"])
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
            tz,
        )
    )
    add(
        _check_time(
            fid,
            "sunset",
            expected["sunset"],
            result.day_events.sunset.iso,
            SUNRISE_SUNSET_TOLERANCE_MINUTES,
            tz,
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
                    tz,
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

    if "tithi_flags" in expected:
        observed = sorted(
            {flag for span in result.tithi for flag in span.flags} & {"kshaya", "vriddhi"}
        )
        add(_check_exact(fid, "tithi.flags", sorted(set(expected["tithi_flags"])), observed))
    if "sunrise_fallback" in expected:
        add(
            _check_exact(
                fid,
                "day_events.sunrise_fallback",
                expected["sunrise_fallback"],
                "sunriseFallbackNearestValidLatitude" in result.day_events.flags,
            )
        )

    return mismatches


def run_fixture(fixture: dict[str, Any]) -> list[Mismatch]:
    request = PanchangRequest(**fixture["request"])
    result = compute_panchang(request)
    return compare_fixture(fixture, result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-gate", action="store_true", help="fail until S1 coverage passes")
    args = parser.parse_args(argv)
    try:
        fixtures = _load_fixtures()
    except (ValueError, KeyError, TypeError) as exc:
        print(f"Invalid reference dataset: {exc}", file=sys.stderr)
        return 1
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
            "\nSee docs/architecture/accuracy-tolerances.md for the tolerance policy and "
            "data/reference_panchang.json (`source_url`) for how to re-derive "
            "the reference values."
        )
        return 1

    print(f"\nAll {len(fixtures)} fixture(s) passed within tolerance.")
    gaps = gate_gaps(fixtures)
    if gaps:
        print("S1 accuracy gate BLOCKED: " + "; ".join(gaps))
        print("Run with --require-gate to enforce the S1 exit gate in CI.")
    else:
        print("S1 accuracy gate PASSED.")
    return int(bool(gaps) and args.require_gate)


if __name__ == "__main__":
    raise SystemExit(main())
