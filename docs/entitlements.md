# The Pandit — Entitlement Matrix

> Authoritative reference for `services/api/src/api/subscriptions/entitlements.py`.
> Any change here must be reflected in the code, and vice-versa.

## Tiers

| Tier | Price point | Billing |
|------|-------------|---------|
| **Basic** | Free | — |
| **Silver** | Mid-tier | Monthly / annual via App Store, Play Store, or Stripe |
| **Gold** | Premium | Monthly / annual via App Store, Play Store, or Stripe |

---

## Entitlement Limits

| Feature | Basic | Silver | Gold |
|---------|-------|--------|------|
| **Panchang look-ahead (days)** | 7 | 90 | 365 |
| **Saved locations** | 1 | 3 | unlimited (`-1`) |
| **Reminders (active)** | 5 | 25 | unlimited (`-1`) |
| **Festival notifications / month** | 5 | 20 | unlimited (`-1`) |
| **PDF calendar exports / month** | 0 | 1 | unlimited (`-1`) |
| **AI Assistant queries / month** | 0 | 5 | unlimited (`-1`) |
| **Family members in vault** | 1 | 5 | unlimited (`-1`) |
| **Muhurat / best-date planning** | ✗ | ✓ | ✓ |
| **Ad-free experience** | ✗ | ✓ | ✓ |
| **Priority Panchang cache** | ✗ | ✗ | ✓ |

### Notes
- `-1` encodes "unlimited" throughout the codebase.
- All limits are enforced server-side by `EntitlementService.check()`; clients
  must never gate on a locally-asserted tier.
- When a subscription expires or is cancelled, the user reverts to **Basic**
  limits immediately (no grace period beyond what the billing provider grants).
- Upgrades take effect immediately upon receipt verification.
- Downgrades (user-initiated or lapse) take effect immediately.

---

## Billing Sources

| Source | Identifier (`source` field) | Sandbox env var prefix |
|--------|-----------------------------|------------------------|
| Apple In-App Purchase | `apple` | `API_APPLE_IAP_*` |
| Google Play Billing | `google` | `API_GOOGLE_PLAY_*` |
| Stripe | `stripe` | `API_STRIPE_*` |

Secrets stored via the managed secret store; never committed.
