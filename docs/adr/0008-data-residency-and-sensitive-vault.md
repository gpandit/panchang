# ADR-0008: Pin sensitive data to an approved regional Vault

- **Status:** Accepted
- **Date:** 2026-10-07
- **Decision area:** Data residency, privacy, and sensitive storage

## Context

Birth date-time-place, family birth data, KYC/background-check evidence, and
exact ceremony addresses are sensitive and may be subject to regional transfer
and deletion requirements. Ordinary application tables, analytics, prompts,
logs, and broad ORM models must not become an accidental second vault.

## Decision

Sensitive payloads are stored only behind a separate Vault interface with
separate credentials, encryption with envelope keys, purpose-scoped access, and
append-only access logging. Ordinary tables contain an opaque `vault_ref_id`,
subject/purpose metadata, approved region, retention state, and non-sensitive
derived display fields only.

Each user and sensitive subject has an assigned approved home region based on
the applicable product/legal policy. Raw Vault payloads, backups, replicas,
provider processing, and support exports remain in that region unless an
explicit legal basis, user policy, and reviewed transfer control permits
otherwise. Cross-region services receive only the minimum derived value or an
opaque reference; analytics receives pseudonymous/aggregated data and never raw
Vault values. Disaster recovery copies follow the same residency policy and
must be included in restore tests.

Exact ceremony addresses are disclosed only to an authorised Pandit during the
stored paid-confirmation window and are hidden after completion. KYC and
background-check adapters return status and references, not raw evidence.
Account export and deletion are region-aware, auditable, and cascade through
derived identifiers, with legally required holds explicitly recorded.

The Vault interface, retention classes, approved regions, transfer mechanisms,
and processor contracts are configuration/policy—not client choices. A change
to residency posture requires privacy/legal review and a superseding ADR.

## Consequences

Regional deployment and provider selection constrain some global architectures,
and support/analytics workflows need carefully scoped tooling. In return, the
system has a clear privacy boundary, auditable access, and a way to meet
region-specific deletion and transfer obligations without duplicating sensitive
payloads.

## Verification and gates

- Schema and serialization tests reject raw Vault values in API responses,
  logs, analytics events, prompts, ordinary exports, and ordinary ORM models.
- Access tests cover purpose, role, region, paid-confirmation window, expiry,
  break-glass audit, deletion, and export.
- S2 privacy tests and S7 data-residency/legal review are release gates; Vault
  fakes are used in local and unit tests.

## References

- `docs/architecture-v3.0.md`, §§1, 4.2, and 7
- `docs/data-model-v3.0.md`, §§1–2 and §8
- `docs/requirements-v3.0.md`, §§2, 3, and 5
- `docs/design-development-plan-v3.0.md`, §§3, 5, and 11
