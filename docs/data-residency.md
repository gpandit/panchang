# Data residency — India & UAE

The Pandit serves users primarily in India and the UAE, both of which carry
specific expectations on where personal data may be stored and processed.

## Expectations

- **India (DPDP Act, 2023):** personal data of Indian users should be
  processed and stored with India-region infrastructure as the default;
  cross-border transfer is permitted to "notified" countries only, and the
  notified list is still evolving. Treat India as a residency region we must
  be able to pin to.
- **UAE (PDPL, Federal Decree-Law No. 45 of 2021):** allows cross-border
  transfer where the destination has an "adequate" data-protection regime or
  appropriate safeguards (e.g. standard contractual clauses) are in place.
  More permissive than India's regime, but still requires a documented basis
  for any transfer out of the UAE.

## What this means for the Users module (Step 2.1)

- `User`, `Location`, vault tables (`vault_birth_profiles`,
  `vault_family_members`, `vault_access_log`) and `account_audit_log` are all
  modelled so that **Postgres can be region-pinned per deployment** — the
  module makes no assumption about a single global database. Production
  topology (single region vs. per-region read/write split) is an
  infrastructure decision to be made before public launch, not an
  application-code one.
- The **vault encryption key** (`API_VAULT_ENCRYPTION_KEY`) is provisioned
  per deployment via the managed secret store — a region split implies
  per-region keys, never a shared global key.
- **Account deletion and data export** (this step) must be wired, when
  multi-region lands, to operate against the user's home region only —
  the service-layer functions (`UserService.delete_account`,
  `UserService.export_data`) are already region-agnostic and operate on
  whatever session they're given.

## Open items (pre-launch gate)

- [ ] Decide single-region vs. India/UAE split topology.
- [ ] Confirm India's "notified country" list covers our chosen UAE/other
      processing locations before any cross-border flow ships.
- [ ] Document the UAE transfer basis (adequacy decision or SCCs) for any
      data that leaves the UAE.

This file tracks expectations only — it is not itself a compliance
sign-off. Legal review is required before the public launch gate.
