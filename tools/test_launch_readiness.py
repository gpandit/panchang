"""Tests for the launch-readiness gate script.

These tests live in tools/ alongside the script they test so they can be run
independently of the panchang service virtualenv.

Run with:  pytest tools/test_launch_readiness.py
"""

import os
import sys
import importlib.util
from pathlib import Path

import pytest

# Load the module directly (it's not a package)
_SCRIPT = Path(__file__).parent / "check_launch_readiness.py"
_spec = importlib.util.spec_from_file_location("check_launch_readiness", _SCRIPT)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]
main = _mod.main


def _run(profile: str, license_: str) -> int:
    os.environ["PANCHANG_BUILD_PROFILE"] = profile
    os.environ["PANCHANG_EPHEMERIS_LICENSE"] = license_
    try:
        return main()
    finally:
        os.environ.pop("PANCHANG_BUILD_PROFILE", None)
        os.environ.pop("PANCHANG_EPHEMERIS_LICENSE", None)


# ── Non-production profiles always pass ──────────────────────────────────────

@pytest.mark.parametrize("profile", ["development", "staging"])
def test_non_production_profile_passes(profile: str, capsys: pytest.CaptureFixture) -> None:
    assert _run(profile, "agpl") == 0


# ── Production + AGPL is blocked ─────────────────────────────────────────────

def test_production_agpl_is_blocked(capsys: pytest.CaptureFixture) -> None:
    exit_code = _run("production", "agpl")
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "LAUNCH GATE BLOCKED" in captured.err


# ── Production + commercial passes ───────────────────────────────────────────

def test_production_commercial_passes(capsys: pytest.CaptureFixture) -> None:
    assert _run("production", "commercial") == 0


# ── Case-insensitive handling ─────────────────────────────────────────────────

def test_case_insensitive_values(capsys: pytest.CaptureFixture) -> None:
    assert _run("PRODUCTION", "AGPL") == 1
    assert _run("Production", "Commercial") == 0
