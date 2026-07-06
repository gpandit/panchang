"""Availability & Scheduling — Architecture v1.2 §1, module 13.

Working hours, blackout dates, lead time, buffer, accept-mode; conflict
prevention / no-double-booking (backed by F2's DB-level exclusion
constraint); optional calendar sync.

F4 ships only the package + a stub :data:`router` (module skeleton). Real
endpoints land in WS-A (A4).
"""

from __future__ import annotations
