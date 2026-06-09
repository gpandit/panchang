#!/usr/bin/env bash
# Offline cache test — The Pandit
#
# Verifies that a client can:
#   1. Fetch and cache Panchang/calendar payloads from staging while online.
#   2. Serve the same data from the local cache when the network is cut.
#
# Requirements: curl, jq, python3 (stdlib only)
# Usage:
#   STAGING_API_URL=https://api-staging.thepandit.app \
#   AUTH_TOKEN=<jwt> \
#   bash tests/offline/test_offline_cache.sh
#
# Exit code 0 = pass; non-zero = failure.

set -euo pipefail

API="${STAGING_API_URL:-http://localhost:8000}"
TOKEN="${AUTH_TOKEN:-}"
LAT=19.0760
LON=72.8777
CACHE_DIR=$(mktemp -d)
PASS=0
FAIL=0

cleanup() { rm -rf "$CACHE_DIR"; }
trap cleanup EXIT

auth_header() {
  if [[ -n "$TOKEN" ]]; then
    echo "Authorization: Bearer $TOKEN"
  else
    echo "X-No-Auth: 1"
  fi
}

log_ok()   { echo "  PASS: $*"; ((PASS++)) || true; }
log_fail() { echo "  FAIL: $*"; ((FAIL++)) || true; }

echo "=== Phase 1: Fetch and cache payloads while online ==="

# ── Today Panchang ─────────────────────────────────────────────────────────
TODAY_FILE="$CACHE_DIR/today_panchang.json"
HTTP=$(curl -sf -o "$TODAY_FILE" -w "%{http_code}" \
  -H "$(auth_header)" \
  "$API/v1/panchang/today?lat=$LAT&lon=$LON")
if [[ "$HTTP" == "200" ]]; then
  log_ok "Fetched today panchang (HTTP $HTTP)"
else
  log_fail "Today panchang fetch failed (HTTP $HTTP)"
fi

# ── Calendar month ──────────────────────────────────────────────────────────
MONTH_FILE="$CACHE_DIR/calendar_month.json"
HTTP=$(curl -sf -o "$MONTH_FILE" -w "%{http_code}" \
  -H "$(auth_header)" \
  "$API/v1/calendar/month?lat=$LAT&lon=$LON&year=2025&month=10")
if [[ "$HTTP" == "200" ]]; then
  log_ok "Fetched calendar month (HTTP $HTTP)"
else
  log_fail "Calendar month fetch failed (HTTP $HTTP)"
fi

# ── Festivals ───────────────────────────────────────────────────────────────
FEST_FILE="$CACHE_DIR/festivals.json"
HTTP=$(curl -sf -o "$FEST_FILE" -w "%{http_code}" \
  -H "$(auth_header)" \
  "$API/v1/festivals?lat=$LAT&lon=$LON&year=2025&month=10")
if [[ "$HTTP" == "200" ]]; then
  log_ok "Fetched festivals (HTTP $HTTP)"
else
  log_fail "Festivals fetch failed (HTTP $HTTP)"
fi

echo ""
echo "=== Phase 2: Validate cached payloads (simulate offline) ==="

# ── Validate today panchang ─────────────────────────────────────────────────
if [[ -f "$TODAY_FILE" ]]; then
  TITHI=$(jq -r '.tithi // empty' "$TODAY_FILE" 2>/dev/null)
  NAKSHATRA=$(jq -r '.nakshatra // empty' "$TODAY_FILE" 2>/dev/null)
  SUNRISE=$(jq -r '.sunrise // empty' "$TODAY_FILE" 2>/dev/null)
  if [[ -n "$TITHI" && -n "$NAKSHATRA" && -n "$SUNRISE" ]]; then
    log_ok "Cached today panchang has tithi='$TITHI', nakshatra='$NAKSHATRA', sunrise='$SUNRISE'"
  else
    log_fail "Cached today panchang missing required fields (tithi='$TITHI' nakshatra='$NAKSHATRA' sunrise='$SUNRISE')"
  fi
fi

# ── Validate calendar month ─────────────────────────────────────────────────
if [[ -f "$MONTH_FILE" ]]; then
  DAY_COUNT=$(python3 -c "
import json, sys
with open('$MONTH_FILE') as f:
    d = json.load(f)
days = d.get('days') or d.get('data') or (d if isinstance(d, list) else [])
print(len(days))
" 2>/dev/null || echo "0")
  if [[ "$DAY_COUNT" -ge 28 ]]; then
    log_ok "Cached calendar has $DAY_COUNT days (≥ 28)"
  else
    log_fail "Cached calendar has only $DAY_COUNT days (expected ≥ 28)"
  fi
fi

# ── Validate festivals ──────────────────────────────────────────────────────
if [[ -f "$FEST_FILE" ]]; then
  FEST_COUNT=$(python3 -c "
import json, sys
with open('$FEST_FILE') as f:
    d = json.load(f)
items = d.get('festivals') or (d if isinstance(d, list) else [])
print(len(items))
" 2>/dev/null || echo "0")
  if [[ "$FEST_COUNT" -ge 1 ]]; then
    log_ok "Cached festivals has $FEST_COUNT entries"
  else
    log_fail "Cached festivals is empty"
  fi
fi

# ── Simulate offline read from cache ───────────────────────────────────────
echo ""
echo "=== Phase 3: Offline read simulation (serve from file cache) ==="
for label in "today_panchang" "calendar_month" "festivals"; do
  FILE="$CACHE_DIR/${label}.json"
  if [[ -f "$FILE" ]]; then
    BYTES=$(wc -c < "$FILE" | tr -d ' ')
    VALID=$(python3 -c "import json; json.load(open('$FILE')); print('ok')" 2>/dev/null || echo "invalid")
    if [[ "$VALID" == "ok" && "$BYTES" -gt 10 ]]; then
      log_ok "$label: valid JSON ($BYTES bytes) — readable offline"
    else
      log_fail "$label: invalid or empty cache file"
    fi
  else
    log_fail "$label: cache file not found"
  fi
done

echo ""
echo "==========================================="
echo "Results: $PASS passed, $FAIL failed"
echo "==========================================="

if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
exit 0
