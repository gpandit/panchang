"""Router stub for the Availability & Scheduling module (F4).

Real endpoints (working hours, blackout dates, availability lookup) land in
WS-A (A4). This module intentionally exposes no routes yet.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/availability", tags=["marketplace-availability"])
