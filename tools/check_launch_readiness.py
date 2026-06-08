#!/usr/bin/env python3
"""Launch-readiness gate: fails any production build until the commercial
Swiss Ephemeris licence is confirmed.

Exit codes:
  0  — gate passed (safe to proceed)
  1  — gate failed (blocked, reason printed to stderr)

Environment variables read (with PANCHANG_ prefix):
  PANCHANG_BUILD_PROFILE       development | staging | production
  PANCHANG_EPHEMERIS_LICENSE   agpl | commercial
"""

import os
import sys

PRODUCTION_PROFILES = {"production"}
GATE_VAR_PROFILE = "PANCHANG_BUILD_PROFILE"
GATE_VAR_LICENSE = "PANCHANG_EPHEMERIS_LICENSE"


def main() -> int:
    profile = os.environ.get(GATE_VAR_PROFILE, "development").strip().lower()
    license_ = os.environ.get(GATE_VAR_LICENSE, "agpl").strip().lower()

    if profile not in PRODUCTION_PROFILES:
        print(f"[launch-gate] profile={profile!r} — not a production build, gate skipped.")
        return 0

    if license_ == "commercial":
        print(
            f"[launch-gate] profile={profile!r}, license={license_!r} — "
            "commercial licence confirmed, gate PASSED."
        )
        return 0

    # Production build + AGPL licence → BLOCK
    print(
        "\n"
        "╔══════════════════════════════════════════════════════════════════╗\n"
        "║            LAUNCH GATE BLOCKED — READ BEFORE PROCEEDING         ║\n"
        "╠══════════════════════════════════════════════════════════════════╣\n"
        f"║  BUILD_PROFILE  : {profile:<47} ║\n"
        f"║  EPHEMERIS_LICENSE: {license_:<45} ║\n"
        "╠══════════════════════════════════════════════════════════════════╣\n"
        "║  The Swiss Ephemeris commercial licence has NOT been confirmed.  ║\n"
        "║  Production / public builds MUST NOT ship under the AGPL build. ║\n"
        "║                                                                  ║\n"
        "║  Action required:                                                ║\n"
        "║    1. Acquire licence from https://www.astro.com/swisseph/       ║\n"
        "║    2. Set PANCHANG_EPHEMERIS_LICENSE=commercial in prod secrets  ║\n"
        "║    3. Close LAUNCH-GATE-001 in the task tracker                  ║\n"
        "║                                                                  ║\n"
        "║  See docs/licensing/swiss-ephemeris.md for full policy.          ║\n"
        "╚══════════════════════════════════════════════════════════════════╝\n",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
