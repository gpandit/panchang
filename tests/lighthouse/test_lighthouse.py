"""Lighthouse budget checks for a public web deployment.

The test is skipped unless ``LIGHTHOUSE_URL`` is supplied.  It uses an already
installed ``lighthouse`` executable (or ``LIGHTHOUSE_BIN``), so a normal CI
run never downloads a browser or needs staging credentials.  Staging jobs can
install Lighthouse separately and opt in with the URL.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

BUDGET = Path(__file__).with_name("lighthouse-budget.json")


def test_lighthouse_budget_is_valid() -> None:
    budget = json.loads(BUDGET.read_text())
    assert set(budget) == {"performance", "accessibility", "best-practices", "seo"}
    assert all(0 <= value <= 1 for value in budget.values())


def test_lighthouse_scores_meet_budget(tmp_path: Path) -> None:
    url = os.environ.get("LIGHTHOUSE_URL")
    if not url:
        pytest.skip("set LIGHTHOUSE_URL to run the staging Lighthouse audit")

    executable = os.environ.get("LIGHTHOUSE_BIN") or shutil.which("lighthouse")
    if not executable:
        pytest.fail("LIGHTHOUSE_URL is set but no lighthouse executable is installed")

    report = tmp_path / "lighthouse.json"
    result = subprocess.run(
        [
            executable,
            url,
            "--output=json",
            f"--output-path={report}",
            "--chrome-flags=--headless --no-sandbox --disable-dev-shm-usage",
        ],
        check=False,
        text=True,
        capture_output=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stderr
    requested_report = os.environ.get("LIGHTHOUSE_REPORT")
    if requested_report:
        destination = Path(requested_report)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(report.read_text())
    scores = json.loads(report.read_text()).get("categories", {})
    budget = json.loads(BUDGET.read_text())
    for category, minimum in budget.items():
        score = scores.get(category, {}).get("score")
        assert score is not None, f"Lighthouse report omitted {category}"
        assert score >= minimum, f"{category} score {score} is below {minimum}"
