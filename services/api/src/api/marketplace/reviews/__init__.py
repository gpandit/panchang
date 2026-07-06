"""Reviews & Ranking — Architecture v1.2 §1, module 20.

Two-way verified-booking reviews with double-blind reveal; aggregates;
moderation (reuses §9.4 flag-and-review); the explainable "recommended"
ranking that feeds B1's default sort.

F4 ships only the package + a stub :data:`router` (module skeleton). Real
endpoints land in WS-D (D3).
"""

from __future__ import annotations
