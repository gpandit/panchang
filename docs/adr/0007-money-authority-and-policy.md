# ADR-0007: Keep money server-authoritative and policy-versioned

- **Status:** Accepted
- **Date:** 2026-10-07
- **Decision area:** Money, commission, pass-through, cancellation, and holdback

## Context

The two marketplaces have different authorities and risk profiles, while
subscriptions use separate payment rails. Client-calculated totals, mutable
commission rules, or a payout released before a dispute/cancellation check
would create financial and audit risk.

## Decision

Commerce Core is the shared money spine for Pandit services and Pooja Items.
All money values use integer minor units and an ISO-4217 currency. The server
computes and stores an itemized quote containing service, travel, samagri,
platform fee, tax, discounts, provider identifiers, currency, and policy
versions. Clients submit selections, never authoritative totals.

Commission, pass-through, tax, cancellation, escrow, holdback, refund, and
payout policies are versioned with effective dates. A confirmed booking/order
stores immutable quote and policy snapshots; later policy edits do not rewrite
history. Pass-through amounts and provider charges are displayed as separate
lines and are included in commission/tax bases only when the versioned policy
explicitly says so. Unknown tax or currency settlement capability blocks or
clearly declines the operation rather than being guessed by a client.

The service-booking default cancellation policy is 100% refund at least 30 days
before the appointment, 50% inside 30 days, and 0% inside 48 hours, subject to
the stored policy snapshot and audited exception/refund flow. Confirmation
captures an authorised payment; completion starts a default 48-hour holdback;
an open dispute freezes payout until resolution. Refunds, transfers, payouts,
and corrections produce append-only ledger evidence and idempotent external
operations. Every journal is double-entry and must balance.

Subscriptions are reconciled separately from marketplace money. Shopify remains
the authority for goods price, inventory, checkout, shipping, and goods tax;
the platform mirrors references and accounts for seller splits without making a
copied product price authoritative.

## Consequences

Quote and policy code is more deliberate, and finance operations must reconcile
provider state with the internal ledger. Users get explainable totals and
consistent refunds. Multi-currency display may be broader than supported
settlement, so that limitation must be surfaced rather than silently converted.

## Verification and gates

- Tests submit tampered client totals and prove the server ignores them.
- Sandbox/fake scenarios cover commission/pass-through, taxes, cancellation
  tiers, partial refunds, failed transfers, disputes, webhook replay, and
  payout holdback; all ledger journals must balance.
- S3 cannot pass until reconciliation is zero and policy/quote snapshots are
  immutable under retries and concurrent transitions.

## References

- `docs/architecture-v3.0.md`, §§4.3, 5.3, 6, and 7
- `docs/design-development-plan-v3.0.md`, §§6 and 8
- `docs/data-model-v3.0.md`, §§5–7
- `docs/requirements-v3.0.md`, §§3, 4.10, and 4.11
