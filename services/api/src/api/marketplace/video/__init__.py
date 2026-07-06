"""Live Video (1:1) — Architecture v1.2 §1, module 21. [P2 fast-follow]

Real-time remote ceremony via an embedded SDK (waiting room, scheduled join
window, session log, optional both-party-consented recording).

F4 ships only the package + a stub :data:`router` (module skeleton). Real
endpoints land in WS-D (D5, Phase 2).
"""

from __future__ import annotations
