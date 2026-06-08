# Contributing to The Pandit

> **Rule zero: engine first, green CI gates every step.**
> Do not advance past a step whose acceptance checks are failing.

---

## §1. Branching model

- `main` — protected; only accepts PRs that pass all required CI checks.
- `staging` — mirrors main after QA sign-off.
- Feature branches: `feature/<short-slug>` (e.g. `feature/stage-0-step-0.1`).
- Fix branches: `fix/<short-slug>`.
- **Never commit directly to `main` or `staging`.**

Each step of the Development Plan is implemented on its own feature branch and merged via a PR once CI is green.

---

## §2. Before you start

```bash
# Install all toolchains
pnpm install
uv sync --all-packages --dev
pre-commit install
```

Read `prompts/00-PROJECT-CONTEXT.md` and the relevant step in the Development Plan before making changes.

---

## §3. Development workflow

1. Branch from `main`: `git checkout -b feature/my-step`
2. Make changes; write tests with the code — every step has "Done when" acceptance checks.
3. Run the full suite locally before pushing:

   ```bash
   pnpm run ci:lint
   pnpm run ci:typecheck
   pnpm run ci:test
   docker compose -f infra/docker-compose.yml up -d
   ```

4. Push and open a PR (draft is fine for in-progress work). Fill in the PR template.
5. CI must be green before requesting review.
6. Mark the PR ready and request review once all acceptance checks pass.

---

## §4. Secrets management

### Local dev
Copy `.env.example` → `.env` at the repo root and in each service directory. Dev defaults are safe for local use only.

### Staging / production
Secrets live in the managed secret store (e.g. AWS Secrets Manager). The CI pipeline reads them via OIDC role assumption — no secrets in environment variables or CI configuration. When adding a new secret:

1. Add a `TODO(secret): <NAME>` comment in the relevant `.env.example`.
2. Add it to the secret store in staging and production.
3. Reference it in the service's `settings.py` via the `pydantic-settings` loader.

**Never commit real credentials.** `pre-commit` runs `detect-secrets` on every commit to catch accidental leaks.

---

## §5. Architecture non-negotiables

These are not up for debate. See `prompts/00-PROJECT-CONTEXT.md` for the full list.

- The **Panchang engine is the single source of astronomical truth.** Only `services/panchang` may call pyswisseph.
- **Clients never recompute Panchang.** All Panchang reads go through `services/api`, which reads the cache.
- **Festivals are rules in a rule engine**, never hard-coded dates.
- **Birth details and family data are encrypted at rest** in a separate vault from the first commit.
- The Swiss Ephemeris **commercial licence must be secured before any public launch build.**

---

## §6. UI/UX exclusion policy

A separate design team (Aqualeo) owns the visual design. Do not invent colours, fonts, spacing, or animations.

- Reference all visual values through named tokens from `packages/design-tokens/tokens.placeholder.json`.
- Mark any placeholder with `// TODO(design): skin via design system`.
- Do not fill in `tokens.placeholder.json` with real values — the design team will replace the whole file.

---

## §7. Testing standards

- **Write tests with the code, not after.**
- Python: pytest, in `tests/` adjacent to `src/`. Async tests use `pytest-asyncio`.
- TypeScript: Vitest, in `tests/` adjacent to `src/`.
- Integration tests against real infrastructure (Postgres, Redis) are tagged `@integration` and run in CI against the docker-compose stack.
- The **Panchang accuracy harness** (Step 1.3) validates computed values against a reference Panchang. It is a required CI check once enabled and gates all merges to `main`.

---

## §8. Commit messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(panchang): compute sunrise using Swiss Ephemeris
fix(api): correct timezone conversion for negative offsets
chore(ci): add accuracy harness job slot
```

Scope is the service or package name: `panchang`, `api`, `web`, `admin`, `api-client-ts`, `ci`, `infra`.

---

## §9. PR checklist

Before marking a PR ready for review:

- [ ] CI is green (lint + typecheck + test)
- [ ] Tests cover the new code paths
- [ ] `.env.example` updated if new env vars were added
- [ ] `README.md` / `CONTRIBUTING.md` updated if behaviour changed
- [ ] No secrets, hard-coded credentials, or `TODO(design)` values filled in
- [ ] Acceptance checks for the current step are all passing
