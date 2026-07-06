"""The "Book a Pandit" marketplace domain package.

F3 lands only the two cross-cutting primitives every later module needs:

* **Dual-role identity** — the :class:`~api.models.auth.Role` enum + the
  ``roles`` JWT claim + the :func:`~api.dependencies.require_role` gateway
  dependency (all defined in the existing ``api.models.auth`` / ``api.auth`` /
  ``api.dependencies`` modules so they sit next to the tier/admin-role logic
  they mirror).
* **Vault references** — :mod:`api.marketplace.vault`, the store-by-reference
  abstraction for sensitive artefacts (ID docs, background-check results, exact
  addresses). Only opaque refs ever leave the vault; the raw value is reachable
  solely through an access-logged read path.

The per-domain module skeleton (providers, verification, bookings, …) and router
registration are **F4's** job — this package intentionally ships nothing else.
"""

from __future__ import annotations
