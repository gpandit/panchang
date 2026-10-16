# Extended readiness checks

The repository's normal unit checks stay credential-free. These focused checks
make the boundaries explicit:

| Check | Local/CI command | External requirement |
| --- | --- | --- |
| Security | `uv run pytest services/api/tests/test_security.py -q` | None |
| Build contract | `uv run pytest tools/test_build_contract.py -q && uv run python tools/check_build_contract.py` | None; set `PANCHANG_RUN_DOCKER_BUILDS=1` for local image builds |
| RLS integration | `PANCHANG_TEST_RLS_URL=postgresql+psycopg://..._test uv run pytest services/api/tests/test_rls.py -v` | Disposable PostgreSQL database named with `_test` |
| Lighthouse | `LIGHTHOUSE_URL=https://staging.example uv run pytest tests/lighthouse -v` | Public staging URL and an installed `lighthouse` executable |

RLS and Lighthouse audits are environment-gated. The self-hosted workflow also
runs dependency/secret scans and the build contract; its Lighthouse job uses the
repository variable `LIGHTHOUSE_URL` or the manual `lighthouse_url` input when
an actual staging audit is desired. These checks do not use production
credentials by default.
