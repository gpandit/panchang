"""Cancellation/Refund Policy Engine — Architecture v1.2 §1, module 18.

30-day reference cancellation/refund policy + configurable inner tiers;
policy **snapshot** stored on each booking; no-show rules.

F4 ships only the package + a stub :data:`router` (module skeleton). Real
endpoints land in WS-C (C4).
"""

from __future__ import annotations
