"""Messaging — Architecture v1.2 §1, module 19.

Per-booking + pre-booking chat (text/images); PII masking + off-platform
leakage detection; retention for dispute evidence.

F4 ships only the package + a stub :data:`router` (module skeleton). Real
endpoints land in WS-D (D1).
"""

from __future__ import annotations
