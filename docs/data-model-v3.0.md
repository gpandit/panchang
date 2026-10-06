# The Pandit — Data Model

**Version:** 3.0 (canonical consolidated model)  
**Date:** 2026-10-07  
**Status:** Logical model for PostgreSQL/PostGIS + Sensitive Vault  
**Rule:** ordinary tables store references to sensitive data, never the sensitive payload.

## 1. Conventions

- UUID primary keys unless a cache/event sequence benefits from a bigint.
- All timestamps are UTC `timestamptz`; retain the relevant IANA timezone and offset at decision
  time. Money uses integer minor units plus ISO-4217 currency.
- Every mutable business row has `created_at`, `updated_at`, and where relevant `version` for
  optimistic concurrency. Financial/audit rows are append-only.
- Every external identifier is namespaced by provider (`stripe_*`, `shopify_*`, etc.) and unique.
- Soft deletion is used for user-owned records where audit/legal retention requires it; erasure
  jobs remove or anonymise data according to policy.

## 2. Identity and privacy schema

| Table | Key fields | Constraints/notes |
|---|---|---|
| `users` | id, auth_subjects, email/phone refs, display_name, locale, tier, roles | unique verified identities; no DOB/TOB/POB |
| `user_preferences` | user_id, scheme, ayanamsa, calendar style, notification settings | one-to-one; validated enum values |
| `locations` | id, user_id, label, lat, lon, timezone, primary | lat/lon bounds; IANA timezone; one primary per user |
| `family_groups` | id, owner_user_id, name, version | owner is admin |
| `family_memberships` | group_id, user_id, role, status, invited_at, accepted_at | admin/member; unique group/user |
| `vault_refs` | id, subject_type, subject_id, region, purpose, provider_ref | opaque pointer only; access policy |
| `vault_access_log` | id, vault_ref_id, actor, purpose, occurred_at | append-only; no payload |
| `devices` | id, user_id, platform, push_token_ref, locale, enabled | token is encrypted/managed; revocable |
| `legal_acceptances` | id, user_id, document, version, accepted_at, ip_hash | immutable evidence |

Sensitive Vault records include user/family birth date-time-place, KYC documents, background-check
references, seller/provider verification artefacts, and exact ceremony addresses. The main database
may store a `vault_ref_id`, derived non-sensitive display fields, region, and retention metadata.

## 3. Panchang, rules, and content

| Table | Key fields | Constraints/notes |
|---|---|---|
| `panchang_days` | date, grid_lat/lon, timezone, ayanamsa, scheme, engine_version, payload | unique canonical cache key; JSONB payload validated against schema |
| `festival_rules` | id, identifier, version, rule_json, scheme, regions, priority, state | unique identifier/version; published versions immutable |
| `festival_occurrences` | rule_id/version, date, grid key, year, anchor_utc, explanation | unique rule version/date/grid; derived and refreshable |
| `festival_content` | festival_id/version, locale, title, body, puja, katha, samagri | only Published is public; source attribution required |
| `content_versions` | entity_type/id, version, author, state, source, diff | immutable provenance |
| `content_flags` | content/version, reporter, reason, state, resolution | moderation queue |
| `vrat_types` | id, identifier, recurrence_rule, content_ref | admin-curated |

The `panchang_days.payload` schema contains arrays of interval objects:

```json
{
  "startUtc": "2026-01-01T02:11:00Z",
  "endUtc": "2026-01-02T01:30:00Z",
  "localOffsetMinutes": 240,
  "hoursFromSunrise": 23.32,
  "flags": ["carriesOver"]
}
```

## 4. User-owned planning data

| Table | Key fields | Constraints/notes |
|---|---|---|
| `notes` | id, owner_user_id, family_group_id?, date_ref, category, body, version | versioned edits; no cross-user leakage |
| `bookmarks` | id, user_id, target_type/id, category | unique user/target/category |
| `reminders` | id, user_id, recurrence_spec, location_id, next_fire_at, fire_key | idempotent fire key; active index |
| `reminder_occurrences` | reminder_id, occurrence_key, fire_at, state | unique reminder/occurrence_key |
| `vrat_records` | id, user_id, vrat_type, occurrence_ref, status, sankalp, notes | status enum and audit timestamps |
| `planner_requests` | id, user_id, event_type, date range, location, preferences | request/audit only; results are reproducible |
| `calendar_jobs` | id, user_id, template, range, options, status, object_ref | async state machine; signed URL generated later |
| `subscriptions` | id, user_id, tier, source, provider_ref, status, expiry | one active entitlement set; provider receipts encrypted/ref-scoped |

## 5. Commerce Core

| Table | Key fields | Constraints/notes |
|---|---|---|
| `provider_accounts` | id, user_id, type, status, stripe_account_ref, kyc_status, standing | type pandit/seller; one account per role/provider |
| `verification_records` | provider_id, kind, vendor, status, vault_ref, expires_at | no raw ID/report data |
| `commission_policies` | id, marketplace, category, rate, pass_through_rules, effective_from | versioned; booking/order snapshots reference policy |
| `tax_records` | aggregate_id, jurisdiction, provider_ref, amount, status | provider response reference; no client authority |
| `payments` | id, aggregate_type/id, intent_ref, status, amount, currency, captured_at | idempotency key unique; append state history |
| `payouts` | id, provider_id, aggregate_ref, amount, currency, hold_until, status | release only after policy/dispute checks |
| `refunds` | id, aggregate_ref, amount, reason, policy_tier, provider_ref, status | immutable decision record |
| `disputes` | id, aggregate_ref, raised_by, state, evidence_refs, resolution | freezes payout until resolution |
| `ledger_journals` | id, aggregate_ref, external_ref, currency, status | balanced journal required |
| `ledger_entries` | journal_id, account, debit_minor, credit_minor | sum debit = sum credit; append-only |
| `outbox_events` | id, aggregate, event_type/version, payload_ref, attempts, state | unique event id; transactional with source mutation |
| `webhook_receipts` | provider, external_event_id, payload_hash, status, processed_at | unique provider/event; signature verified before process |

Ledger accounts include `patron_receivable`, `escrow`, `platform_revenue`,
`provider_payable:{id}`, `seller_payable:{id}`, `tax_payable`, and `refunds`. Subscription billing
uses a separate ledger/reconciliation domain.

## 6. Pandit Services marketplace

| Table | Key fields | Constraints/notes |
|---|---|---|
| `pandits` | provider_id, display_name, bio, base_location_id, languages, traditions, approval | discoverable only Approved + Verified |
| `service_types` | id, name, category, festival_refs, muhurat_types, default duration | admin taxonomy |
| `pandit_services` | pandit_id, service_type_id, modes, duration, base price, currency, samagri | active only after provider approval |
| `travel_policies` | pandit_id, radius_miles, fee_model, bands, pickup_required | radius ≤100; PostGIS distance |
| `availability_rules` | pandit_id, weekly hours, lead time, buffer, acceptance mode | validated recurrence |
| `availability_blackouts` | pandit_id, start/end, reason | indexed range |
| `bookings` | id, patron_id, pandit_id, service_id, mode, start/end UTC, state, quote_snapshot, policy_snapshot, address_vault_ref | exclusion/range constraint for active states |
| `booking_events` | booking_id, from/to state, actor, reason, at | append-only; same transaction as transition |
| `booking_holds` | booking_id, slot range, expires_at | unique active hold; released/expired idempotently |
| `reviews` | booking_id, author role, stars, body, moderation, reveal_at | verified booking; one per side |
| `conversations` | id, booking/enquiry ref, participants, state | access-scoped |
| `messages` | conversation_id, sender, masked body, attachment_ref, flags | PII masking and retention |
| `video_sessions` | booking_id, provider, room_ref, join log, recording_ref | Phase 2; recording opt-in |

Active booking states (`requested`, `confirmed`, `reschedule_pending`, `in_progress`) must not
overlap for one Pandit. Use PostgreSQL range/exclusion enforcement plus application locks; tests
must prove 50 concurrent attempts yield exactly one confirmed booking.

### 6.1 Booking and quote invariants

- Quote totals are recomputed server-side; client totals are display-only.
- `policy_snapshot`, `quote_snapshot`, tax, commission, currency, and provider identifiers are
  immutable after confirmation except through an audited correction/refund flow.
- `requested` authorises payment; confirmation captures; completion starts a 48-hour default
  holdback; disputes freeze payout.
- Exact address is a Vault ref and is readable by the Pandit only during the authorised window.

## 7. Pooja Items marketplace

| Table | Key fields | Constraints/notes |
|---|---|---|
| `sellers` | provider_id, shop name, approval, standing | Shopify-backed |
| `product_refs` | Shopify product/variant ids, seller, category, festival refs, product type | no authoritative price/inventory copy |
| `order_refs` | Shopify order id, buyer, status, totals snapshot, tax ref | Shopify remains source of truth |
| `order_seller_splits` | order, seller, line refs, commission, payout status | one split per seller/order |
| `fulfillments` | split, carrier, tracking, status, timestamps | write-through to Shopify |
| `return_requests` | order, lines, reason, state, refund ref | policy/audit |
| `product_reviews` | product, buyer, order ref, stars, body, moderation | verified purchase |

`SamagriList` is CMS data mapping festival/service items to optional Shopify variant IDs. Checkout
always returns a Shopify-hosted checkout URL. Shopify signed webhooks create/update mirrors,
ledger entries, seller splits, notifications, and payout eligibility.

## 8. Indexes, retention, and migrations

Required indexes include cache key uniqueness, occurrence date/grid, reminder active/next-fire,
user-owned date queries, booking provider/time/state, PostGIS provider locations, webhook provider
event, outbox state/created time, ledger aggregate, and order buyer/seller. Use additive,
backward-compatible migrations, backfill before constraint enforcement, and expand/contract for
zero-downtime changes. Retention and deletion jobs must be tested for messages, logs, vault refs,
and derived analytics.

## 9. Required model-level checks

1. panchang payload validates UTC/offset/hours-from-sunrise consistency;
2. festival published content has a published rule/version and source attribution;
3. Basic tier limits cannot be bypassed by client-supplied counts;
4. family membership and note access enforce group permissions;
5. booking range exclusion and idempotency hold under concurrency;
6. every ledger journal balances to zero;
7. webhook replay is harmless;
8. vault raw values cannot appear in API schemas, logs, analytics, or exports.
