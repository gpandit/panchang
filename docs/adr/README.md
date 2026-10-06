# Architecture Decision Records

These records are the accepted S0-01 architecture decisions for The Pandit v3.0
baseline. They make the contracts in the v3.0 requirements, architecture, data
model, and development plan explicit for implementation and review.

An ADR is accepted when it is merged into the repository. A later decision must
supersede the relevant record rather than silently changing an invariant. Code,
tests, migrations, OpenAPI, and operational runbooks should link to the relevant
ADR when they implement one of these boundaries.

## Accepted decisions

| ADR | Decision |
|---|---|
| [0001](0001-backend-modular-monolith.md) | Python/FastAPI modular monolith first |
| [0002](0002-native-mobile-clients.md) | Retain native SwiftUI and Kotlin/Compose clients |
| [0003](0003-panchang-cache-grid.md) | Canonical PCS cache with configurable 0.1° grid |
| [0004](0004-panchang-accuracy-contract.md) | Executable Panchang accuracy tolerances |
| [0005](0005-transactional-outbox-eventing.md) | Transactional outbox before a managed event bus |
| [0006](0006-external-provider-boundaries.md) | Provider-neutral ports and adapter-owned vendors |
| [0007](0007-money-authority-and-policy.md) | Server-authoritative quotes, ledger, and payout policy |
| [0008](0008-data-residency-and-sensitive-vault.md) | Region-pinned sensitive data behind a Vault boundary |
| [0009](0009-ai-retention-and-retrieval.md) | Minimized, opt-in AI retention with grounded retrieval |

## Decision scope

These ADRs cover the S0-01 decisions called out by
`docs/design-development-plan-v3.0.md`. They do not claim that the associated
features are implemented. The stage gate remains evidence-based: migrations,
contracts, tests, accuracy fixtures, and provider/compliance sign-offs must be
completed by their respective stage.
