"""Router stub for the Verification & Trust (KYC) module (F4).

Real endpoints (verification submission, webhook ingestion) land in WS-A (A2).
This module intentionally exposes no routes yet.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/verification", tags=["marketplace-verification"])
