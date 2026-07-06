"""Router stub for the Booking & Lifecycle module (F4).

Real endpoints (booking creation, reschedule/cancel) land in WS-B (B3, B4);
the lifecycle state machine lands in WS-C (C1). This module intentionally
exposes no routes yet.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/bookings", tags=["marketplace-bookings"])
