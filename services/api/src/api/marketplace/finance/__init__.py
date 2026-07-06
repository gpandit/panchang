"""Tax & Finance — Architecture v1.2 §1, module 23.

Marketplace-facilitator sales tax (US), VAT (UK/EU), platform-fee vs
earnings treatment, multi-currency display/settlement, provider tax
reporting (1099-K via Stripe).

F4 ships only the package + a stub :data:`router` (module skeleton). Real
endpoints land in WS-C (C5).
"""

from __future__ import annotations
