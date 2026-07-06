"""Router stub for the Cancellation/Refund Policy Engine module (F4).

Real endpoints (cancel/refund computation from the booking's policy
snapshot) land in WS-C (C4). This module intentionally exposes no routes yet.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/policy", tags=["marketplace-policy"])
