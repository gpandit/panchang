# tools/

Scripts, code generators, and harness runners for The Pandit monorepo.

## Offline S0-06 authority check

From the repository root, with Python 3.11+ and no external services or packages:

```sh
python3 tools/check_contract_authority.py
python3 -m unittest tools.test_contract_authority -v
```

The checker exits nonzero on an ephemeris import outside `services/panchang` or
client authority patterns in `apps/web/src`, `apps/admin/src`,
`apps/temple-admin/src`, iOS app sources, and Android main sources. It ignores
documentation, comments, string literals, generated/vendor output, and client
tests. Legitimate Next.js server rendering of gateway values is allowed. It checks
source patterns, not full data flow: dynamic module names and calculations
hidden behind generic helper names still need review. The Python 3.12 AST is
used when available; older local interpreters tokenize Python 3.12 syntax.

## Other tools

- `accuracy_harness/` — Panchang accuracy validation runner (Step 1.3)
- `codegen/` — OpenAPI → TypeScript client generator (Step 2)
- `seed/` — local database seed scripts for dev

Additional scripts are added alongside their development steps.
