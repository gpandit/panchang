"""Router stub for the Trust, Safety & Disputes module (F4).

Real endpoints (address-privacy gate, dispute workflow, standing score) land
in WS-D (D4). This module intentionally exposes no routes yet.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/safety", tags=["marketplace-safety"])
