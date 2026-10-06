# ADR-0006: Isolate external vendors behind provider ports

- **Status:** Accepted
- **Date:** 2026-10-07
- **Decision area:** Vendor and integration boundaries

## Context

The product uses different external authorities and payment rails: Swiss
Ephemeris, Apple/Google/Stripe subscriptions, Stripe Connect for services,
Shopify for goods, KYC and tax providers, notification providers, optional
video, and LLM/embedding providers. Domain rules must remain portable,
testable, and protected from vendor SDK semantics or an unplanned vendor
replacement.

## Decision

Each external capability is represented by a narrow, provider-neutral port in
the owning domain and implemented by an adapter. Vendor SDKs, credentials,
webhook verification, rate limits, retries, external IDs, and provider-specific
payloads stay in adapters. External identifiers are namespaced by provider and
raw credentials, card data, KYC documents, and vendor payloads do not enter
ordinary domain models.

The authority boundaries are explicit:

- PCS is the only component allowed to call Swiss Ephemeris; the commercial
  licence is a production launch gate.
- Apple IAP, Google Play Billing, and Stripe Web reconcile subscriptions into
  one server entitlement; clients never assert their tier.
- Stripe Connect handles service payment rails through Commerce Core; it does
  not own booking policy or the internal ledger.
- Shopify remains authoritative for goods catalogue, price, inventory, cart,
  checkout, shipping, tax, and fulfilment; the platform stores references and
  mirrors, not an authoritative copied price.
- KYC, tax, notifications, video, LLM, embeddings, and object storage are
  replaceable adapters. Video recording is opt-in and off by default.

Every integration starts with deterministic fakes and signed/replayable
fixtures. Production adapters are enabled only after the provider contract,
data-processing/residency review, reconciliation behavior, and failure mode are
documented. Marketplace modules call ports directly; they do not make HTTP
loopback calls to themselves.

## Consequences

Adapters add mapping and contract-test work, but domain tests run without live
credentials and vendor changes do not rewrite core policy. The platform must
track provider outages, webhook gaps, reconciliation, and version drift. A
vendor-specific feature is not part of the core contract until its behavior is
expressed in a provider-neutral port or explicitly accepted by a new ADR.

## Verification and gates

- Forbidden-import and dependency checks keep vendor SDKs out of domain modules.
- Fakes cover success, timeout, duplicate webhook, signature failure, partial
  refund, failed transfer, and provider outage paths.
- S3–S7 gates require sandbox evidence, reconciliation, security/privacy review,
  and commercial licensing where applicable.

## References

- `docs/architecture-v3.0.md`, §§3–4 and §9
- `docs/design-development-plan-v3.0.md`, §§3 and 6–11
- `docs/requirements-v3.0.md`, §§1.1, 3, 4.8, 4.10–4.12, and 5
- `docs/licensing/swiss-ephemeris.md`
