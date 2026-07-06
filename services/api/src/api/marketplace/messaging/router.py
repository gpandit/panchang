"""Router stub for the Messaging module (F4).

Real endpoints (conversation/message CRUD, PII masking) land in WS-D (D1).
This module intentionally exposes no routes yet.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/messaging", tags=["marketplace-messaging"])
