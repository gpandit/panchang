"""Quote & Pricing Engine — Architecture v1.2 §1, module 16.

Server-side itemised quote: base + travel + samagri + platform fee + tax.
Authoritative; the client never computes or sets an amount (north-star #5).

F4 ships only the package + a stub :data:`router` (module skeleton). The
Quote schema is frozen and the engine built in WS-B (B3).
"""

from __future__ import annotations
