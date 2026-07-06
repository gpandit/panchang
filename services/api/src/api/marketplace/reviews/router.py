"""Router stub for the Reviews & Ranking module (F4).

Real endpoints (review submission, double-blind reveal, ranking) land in
WS-D (D3). This module intentionally exposes no routes yet.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/reviews", tags=["marketplace-reviews"])
