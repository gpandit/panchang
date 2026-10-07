"""Validate the user-supplied multi-timezone phase conversion fixture."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

FIXTURE = (
    Path(__file__).parents[3]
    / "tools"
    / "accuracy_harness"
    / "data"
    / "timezone_conversion_20261007.json"
)
PHASES = ("tithi", "nakshatra", "yoga", "karana_1", "karana_2")


def _load() -> list[dict[str, object]]:
    payload = json.loads(FIXTURE.read_text())
    assert (
        payload["_meta"]["purpose"]
        == "Validate aware local timestamps, IANA offsets, and UTC normalization."
    )
    return payload["records"]


def test_fixture_has_ten_distinct_timezones_and_valid_local_offsets() -> None:
    records = _load()
    assert len(records) == 10
    assert len({record["id"] for record in records}) == 10
    assert len({record["location"]["timezone"] for record in records}) == 10

    for record in records:
        location = record["location"]
        tz = ZoneInfo(location["timezone"])
        local_day = date.fromisoformat(record["date"])
        sunrise = datetime.combine(
            local_day, time.fromisoformat(record["sun_metrics"]["sunrise"]), tzinfo=tz
        )
        sunset = datetime.combine(
            local_day, time.fromisoformat(record["sun_metrics"]["sunset"]), tzinfo=tz
        )
        offset_marker = datetime.fromisoformat(f"2000-01-01T00:00:00{location['utc_offset']}")
        expected_offset = offset_marker.utcoffset()
        assert expected_offset is not None
        assert sunrise.utcoffset() == expected_offset
        assert sunset.utcoffset() == expected_offset
        assert sunset > sunrise


def test_phase_endings_normalize_to_one_utc_instant_per_phase() -> None:
    records = _load()
    for phase in PHASES:
        instants = {
            datetime.fromisoformat(record["endings"][phase]["at"]).astimezone(UTC)
            for record in records
        }
        assert len(instants) == 1, (phase, sorted(instants))

    assert (
        datetime.fromisoformat(records[0]["endings"]["tithi"]["at"]).astimezone(UTC).isoformat()
        == "2026-10-07T17:46:00+00:00"
    )
