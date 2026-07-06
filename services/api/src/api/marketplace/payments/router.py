"""Router stub for the Payments, Escrow & Payouts module (F4).

Real endpoints (Stripe Connect onboarding, escrow, webhooks) land in WS-C
(C2, C3). This module intentionally exposes no routes yet.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/payments", tags=["marketplace-payments"])
