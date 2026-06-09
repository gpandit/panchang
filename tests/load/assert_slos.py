"""Assert SLO targets from a Locust CSV stats file.

Exit code 0 = all targets met; non-zero = failure (CI will fail the job).

Usage:
  python tests/load/assert_slos.py tests/load/results_stats.csv
"""

from __future__ import annotations

import csv
import sys

# SLO targets per endpoint (all in milliseconds)
SLOS: dict[str, dict[str, float]] = {
    "/v1/panchang/today": {"p50": 100, "p95": 300, "p99": 500, "error_pct": 0.5},
    "/v1/calendar/month": {"p50": 150, "p95": 500, "p99": 800, "error_pct": 0.5},
    "/v1/festivals":      {"p50": 100, "p95": 300, "p99": 500, "error_pct": 0.5},
}


def main(csv_path: str) -> int:
    failures: list[str] = []

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = {row["Name"]: row for row in reader}

    for endpoint, targets in SLOS.items():
        row = rows.get(endpoint)
        if row is None:
            print(f"WARN: no data for {endpoint} — skipping")
            continue

        p50 = float(row.get("50%", 0))
        p95 = float(row.get("95%", 0))
        p99 = float(row.get("99%", 0))
        total = int(row.get("Request Count", 0)) or 1
        errors = int(row.get("Failure Count", 0))
        error_pct = 100.0 * errors / total

        checks = [
            ("p50", p50, targets["p50"]),
            ("p95", p95, targets["p95"]),
            ("p99", p99, targets["p99"]),
        ]
        for label, actual, limit in checks:
            if actual > limit:
                failures.append(
                    f"FAIL {endpoint} {label}: {actual:.0f} ms > {limit:.0f} ms"
                )
            else:
                print(f"  OK {endpoint} {label}: {actual:.0f} ms (≤ {limit:.0f} ms)")

        if error_pct > targets["error_pct"]:
            failures.append(
                f"FAIL {endpoint} error rate: {error_pct:.2f}% > {targets['error_pct']}%"
            )
        else:
            print(f"  OK {endpoint} error rate: {error_pct:.2f}% (≤ {targets['error_pct']}%)")

    if failures:
        print("\nSLO violations:")
        for f in failures:
            print(" ", f)
        return 1

    print("\nAll SLO targets met.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <locust-results_stats.csv>")
        sys.exit(1)
    sys.exit(main(sys.argv[1]))
