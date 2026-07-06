"""Router stub for the Discovery & Search module (F4).

Real endpoints (filtered/sorted pandit search) land in WS-B (B1). This module
intentionally exposes no routes yet.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/search", tags=["marketplace-search"])
