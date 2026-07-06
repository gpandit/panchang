"""Router stub for the Provider (Pandit) Profile & Catalogue module (F4).

Real endpoints (onboarding, catalogue CRUD) land in WS-A (A1, A3). This module
intentionally exposes no routes yet — it exists so the package is registered
and importable from :mod:`api.main`.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/providers", tags=["marketplace-providers"])
