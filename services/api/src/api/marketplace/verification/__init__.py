"""Verification & Trust (KYC) — Architecture v1.2 §1, module 12.

Government-ID + selfie liveness, background check (US/UK), address
verification, credential attestation, re-verification cadence. Writes refs to
the Vault (:mod:`api.marketplace.vault`).

F4 ships only the package + a stub :data:`router` (module skeleton). Real
endpoints land in WS-A (A2).
"""

from __future__ import annotations
