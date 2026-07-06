"""Booking & Lifecycle — Architecture v1.2 §1, module 15.

Booking creation, the explicit state machine (§A5), ``BookingEvent`` audit,
reschedule/cancel, recurring/rebook.

F4 ships only the package + a stub :data:`router` (module skeleton). Real
endpoints land in WS-B (B3, B4) and the lifecycle state machine in WS-C (C1).
"""

from __future__ import annotations
