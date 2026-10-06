# ADR-0009: Minimize AI retention and ground retrieval in published content

- **Status:** Accepted
- **Date:** 2026-10-07
- **Decision area:** AI, retrieval, and retention

## Context

Ask The Pandit needs an LLM and embeddings without coupling the product to a
single vendor or allowing unreviewed ritual claims. Prompts can contain
personal or sensitive information, while provider logs may persist outside the
application's control. The v3.0 requirements call for grounded answers,
source citations, and opt-in or redacted query retention.

## Decision

Use provider-neutral LLM, embedding, and retrieval ports. The initial retrieval
boundary is PostgreSQL/pgvector-compatible; a managed vector vendor is not a
core dependency. Only published, source-attributed CMS content and approved
structured Panchang outputs are eligible for indexing. Each chunk stores source
identity/version, locale/region, and policy metadata so publication correction
or withdrawal can invalidate dependent embeddings.

The default is no raw prompt or response retention. The service may retain
minimal pseudonymous operational metadata—request ID, region, policy outcome,
model/provider identifier, latency, and token counts—for reliability and
billing controls. A user can explicitly opt in to a bounded, redacted history;
the retention period, purpose, export, and deletion behavior are disclosed and
enforced. Sensitive Vault values are never sent to an LLM or embedding
provider. Input filters redact or reject birth data, KYC, exact addresses,
secrets, payment data, and other protected values before a model call.

Production providers must contractually disable training on The Pandit's data,
provide a documented retention/deletion behavior, and satisfy the assigned data
residency policy. Provider logs are treated as a processor boundary and are not
assumed to be erased merely because the application deleted a row. AI output
must cite sources, identify regional variation, decline unsupported ritual
claims, state when grounding is unavailable, and include the qualified-pandit/
family-tradition disclaimer where appropriate.

## Consequences

Default privacy is stronger and the system can change model/vector vendors, but
conversation replay and debugging are limited without opt-in history. Index
refresh and source-version tracking are mandatory. Prompt filtering can reduce
answer context; the assistant should explain a refusal rather than bypassing
the Vault boundary.

## Verification and gates

- Contract tests run against deterministic LLM/embedding fakes and assert source
  citations, refusal behavior, redaction, region routing, and no sensitive
  payload leakage.
- Retention tests cover default deletion, opt-in expiry, export, account
  deletion, source withdrawal, and provider failure/retry.
- S6 AI work and S7 privacy/compliance review cannot pass with raw prompts in
  logs or an unapproved provider retention/training posture.

## References

- `docs/architecture-v3.0.md`, §§3, 4.2, 6, and 7
- `docs/design-development-plan-v3.0.md`, §9 and §11
- `docs/requirements-v3.0.md`, §§1.1, 4.12, and 5
- `docs/data-model-v3.0.md`, §§1–2 and §8
