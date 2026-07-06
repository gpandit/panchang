"""Router stub for the Quote & Pricing Engine module (F4).

Real endpoints (server-authoritative quote computation) land in WS-B (B3).
This module intentionally exposes no routes yet.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/pricing", tags=["marketplace-pricing"])
