"""Festival-spike load test — The Pandit Panchang + calendar read paths.

Simulates the burst of traffic around a major festival (e.g. Diwali) when
thousands of users simultaneously fetch today's Panchang, the current calendar
month, and the festival listing.

Target SLOs (enforced by assert_slos.py):
  - p50 < 100 ms
  - p95 < 300 ms
  - p99 < 500 ms
  - Error rate < 0.5 %

Run:
  locust -f tests/load/festival_spike.py --headless \
         --users 200 --spawn-rate 20 --run-time 120s \
         --host https://api-staging.thepandit.app \
         --html tests/load/report.html --csv tests/load/results
"""

from __future__ import annotations

import os
import random

from locust import HttpUser, between, task

# Mumbai lat/lon as a default; spike traffic spreads across major cities
CITIES = [
    (19.0760, 72.8777),   # Mumbai
    (28.6139, 77.2090),   # Delhi
    (12.9716, 77.5946),   # Bangalore
    (17.3850, 78.4867),   # Hyderabad
    (13.0827, 80.2707),   # Chennai
    (22.5726, 88.3639),   # Kolkata
    (23.0225, 72.5714),   # Ahmedabad
    (18.5204, 73.8567),   # Pune
]

# Months to request — spike tends to hit near festival months
MONTHS = [9, 10, 11]  # Sep–Nov (Navratri / Diwali window)

# JWT for load test — use a shared read-only test account or anonymous token
_AUTH_TOKEN = os.environ.get("LOAD_TEST_JWT", "")


class PanchangReadUser(HttpUser):
    """Simulates a user who opens the app during a festival spike."""

    wait_time = between(0.5, 2.0)

    def on_start(self) -> None:
        lat, lon = random.choice(CITIES)
        self.lat = lat
        self.lon = lon
        self.month = random.choice(MONTHS)
        if _AUTH_TOKEN:
            self.client.headers["Authorization"] = f"Bearer {_AUTH_TOKEN}"

    @task(5)
    def today_panchang(self) -> None:
        """Highest-frequency read: the Today screen."""
        with self.client.get(
            "/v1/panchang/today",
            params={"lat": self.lat, "lon": self.lon},
            name="/v1/panchang/today",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"Status {r.status_code}")
            elif "tithi" not in r.text:
                r.failure("Response missing tithi field")

    @task(3)
    def calendar_month(self) -> None:
        """Calendar month view — slightly less frequent than Today."""
        with self.client.get(
            "/v1/calendar/month",
            params={
                "lat": self.lat,
                "lon": self.lon,
                "year": 2025,
                "month": self.month,
            },
            name="/v1/calendar/month",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"Status {r.status_code}")

    @task(2)
    def festivals_month(self) -> None:
        """Festival listing for the current month."""
        with self.client.get(
            "/v1/festivals",
            params={
                "lat": self.lat,
                "lon": self.lon,
                "year": 2025,
                "month": self.month,
            },
            name="/v1/festivals",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"Status {r.status_code}")

    @task(1)
    def single_day_panchang(self) -> None:
        """Occasional single-day detail fetch."""
        day = random.randint(1, 28)
        with self.client.get(
            f"/v1/panchang/2025/10/{day:02d}",
            params={"lat": self.lat, "lon": self.lon},
            name="/v1/panchang/{date}",
            catch_response=True,
        ) as r:
            if r.status_code not in (200, 404):
                r.failure(f"Status {r.status_code}")
