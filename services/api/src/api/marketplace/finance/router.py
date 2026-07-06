"""Router stub for the Tax & Finance module (F4).

Real endpoints (tax config, multi-currency, provider tax reporting) land in
WS-C (C5). This module intentionally exposes no routes yet.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/finance", tags=["marketplace-finance"])
