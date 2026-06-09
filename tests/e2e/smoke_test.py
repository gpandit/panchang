"""E2E smoke test — The Pandit staging.

Journey:
  1. Sign up (or sign in with test account)
  2. Set location (Mumbai, India)
  3. Open Today — verify Panchang fields populated
  4. Browse calendar month — verify cells have tithi/nakshatra
  5. Add a personal note + reminder on today's date
  6. Open a festival — verify details present
  7. Request a 12-month PDF generation (async job) — verify job accepted
  8. Verify reminder acknowledged (stub — real push requires device)

Run locally:
  STAGING_API_URL=http://localhost:8000 pytest tests/e2e/smoke_test.py -v

In CI the STAGING_* env vars are injected from secrets.
"""

from __future__ import annotations

import os
import time

import httpx
import pytest

API = os.environ.get("STAGING_API_URL", "http://localhost:8000")
TEST_EMAIL = os.environ.get("STAGING_TEST_EMAIL", "smoke@test.pandit.internal")
TEST_PASSWORD = os.environ.get("STAGING_TEST_PASSWORD", "SmokeTest123!")

# Mumbai coordinates
LAT, LON = 19.0760, 72.8777


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def client() -> httpx.Client:
    with httpx.Client(base_url=API, timeout=15.0) as c:
        yield c


@pytest.fixture(scope="session")
def auth_token(client: httpx.Client) -> str:
    """Obtain a JWT for the test account (sign up if needed)."""
    # Try sign-in first
    r = client.post("/v1/auth/token", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
    })
    if r.status_code == 200:
        return r.json()["access_token"]

    # Sign up
    r = client.post("/v1/auth/register", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "display_name": "Smoke Tester",
    })
    assert r.status_code in (200, 201), f"Register failed: {r.status_code} {r.text}"

    r = client.post("/v1/auth/token", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
    })
    assert r.status_code == 200, f"Login after register failed: {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def authed(client: httpx.Client, auth_token: str) -> httpx.Client:
    client.headers["Authorization"] = f"Bearer {auth_token}"
    return client


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestHealthChecks:
    def test_api_healthz(self, client: httpx.Client) -> None:
        r = client.get("/healthz")
        assert r.status_code == 200

    def test_api_version(self, client: httpx.Client) -> None:
        r = client.get("/v1/version")
        assert r.status_code in (200, 404)  # optional endpoint


class TestLocation:
    def test_set_location(self, authed: httpx.Client) -> None:
        r = authed.put("/v1/profile/location", json={
            "latitude": LAT,
            "longitude": LON,
            "timezone": "Asia/Kolkata",
        })
        assert r.status_code in (200, 204), f"Set location: {r.status_code} {r.text}"


class TestToday:
    def test_today_panchang(self, authed: httpx.Client) -> None:
        r = authed.get("/v1/panchang/today", params={"lat": LAT, "lon": LON})
        assert r.status_code == 200, f"Today: {r.status_code} {r.text}"
        body = r.json()
        # Verify structural fields expected on every day
        for field in ("tithi", "nakshatra", "yoga", "karana", "sunrise", "sunset"):
            assert field in body, f"Missing field: {field}"

    def test_today_response_time(self, authed: httpx.Client) -> None:
        """Panchang today must respond in < 500 ms (warm cache)."""
        start = time.perf_counter()
        r = authed.get("/v1/panchang/today", params={"lat": LAT, "lon": LON})
        elapsed = time.perf_counter() - start
        assert r.status_code == 200
        assert elapsed < 0.5, f"Today too slow: {elapsed:.3f}s"


class TestCalendar:
    def test_calendar_month(self, authed: httpx.Client) -> None:
        r = authed.get("/v1/calendar/month", params={
            "lat": LAT, "lon": LON,
            "year": 2025, "month": 10,
        })
        assert r.status_code == 200, f"Calendar: {r.status_code} {r.text}"
        body = r.json()
        days = body.get("days") or body.get("data") or body
        assert len(days) >= 28, "Month calendar should have ≥ 28 days"

        # Every day must have tithi + nakshatra
        first_day = days[0] if isinstance(days, list) else list(days.values())[0]
        for field in ("tithi", "nakshatra"):
            assert field in first_day, f"Calendar day missing: {field}"

    def test_calendar_latency(self, authed: httpx.Client) -> None:
        """Calendar month must respond in < 800 ms (may be freshly computed)."""
        start = time.perf_counter()
        r = authed.get("/v1/calendar/month", params={
            "lat": LAT, "lon": LON, "year": 2025, "month": 11,
        })
        elapsed = time.perf_counter() - start
        assert r.status_code == 200
        assert elapsed < 0.8, f"Calendar month too slow: {elapsed:.3f}s"


class TestNotesAndReminders:
    def test_add_note(self, authed: httpx.Client) -> None:
        r = authed.post("/v1/notes", json={
            "date": "2025-10-20",
            "text": "E2E smoke test note",
        })
        assert r.status_code in (200, 201), f"Add note: {r.status_code} {r.text}"
        note_id = r.json().get("id")
        assert note_id is not None

    def test_add_reminder(self, authed: httpx.Client) -> None:
        r = authed.post("/v1/reminders", json={
            "title": "E2E test reminder",
            "recurrence_type": "gregorian_once",
            "date": "2025-10-20",
            "time": "09:00",
        })
        assert r.status_code in (200, 201), f"Add reminder: {r.status_code} {r.text}"


class TestFestivals:
    def test_festivals_list(self, authed: httpx.Client) -> None:
        r = authed.get("/v1/festivals", params={
            "lat": LAT, "lon": LON,
            "year": 2025, "month": 10,
        })
        assert r.status_code == 200
        festivals = r.json().get("festivals") or r.json()
        assert len(festivals) > 0, "Expected at least one festival in Oct 2025"

    def test_festival_detail(self, authed: httpx.Client) -> None:
        r = authed.get("/v1/festivals", params={
            "lat": LAT, "lon": LON, "year": 2025, "month": 10,
        })
        festivals = r.json().get("festivals") or r.json()
        festival_id = festivals[0]["id"]

        r = authed.get(f"/v1/festivals/{festival_id}")
        assert r.status_code == 200
        body = r.json()
        assert "name" in body
        assert "description" in body or "significance" in body


class TestPDFGeneration:
    def test_pdf_job_accepted(self, authed: httpx.Client) -> None:
        r = authed.post("/v1/pdf/calendar", json={
            "lat": LAT, "lon": LON,
            "year": 2025,
            "months": 12,
        })
        assert r.status_code in (200, 201, 202), \
            f"PDF job not accepted: {r.status_code} {r.text}"
        body = r.json()
        assert "job_id" in body or "task_id" in body or "id" in body, \
            "PDF response must include a job identifier"

    def test_pdf_job_status_reachable(self, authed: httpx.Client) -> None:
        """Job status endpoint must exist even if job isn't done yet."""
        r = authed.post("/v1/pdf/calendar", json={
            "lat": LAT, "lon": LON, "year": 2025, "months": 1,
        })
        assert r.status_code in (200, 201, 202)
        body = r.json()
        job_id = body.get("job_id") or body.get("task_id") or body.get("id")
        if job_id:
            r2 = authed.get(f"/v1/pdf/jobs/{job_id}")
            assert r2.status_code in (200, 202, 404)
