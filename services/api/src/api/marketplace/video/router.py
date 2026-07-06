"""Router stub for the Live Video (1:1) module (F4). [P2 fast-follow]

Real endpoints (session join, waiting room, recording) land in WS-D (D5,
Phase 2). This module intentionally exposes no routes yet.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/video", tags=["marketplace-video"])
