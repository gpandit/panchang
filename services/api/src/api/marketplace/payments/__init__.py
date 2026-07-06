"""Payments, Escrow & Payouts — Architecture v1.2 §1, module 17.

Stripe Connect escrow (authorise -> capture -> hold -> release), commission
take-rate, payouts, refunds, webhooks, idempotency, reconciliation into the
§12 ledger pattern.

F4 ships only the package + a stub :data:`router` (module skeleton). Real
endpoints land in WS-C (C2, C3).
"""

from __future__ import annotations
