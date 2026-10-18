# Self-hosted GitHub Actions runner

The repository keeps the standard GitHub-hosted CI workflow and also provides a
separate self-hosted validation workflow at
`.github/workflows/self-hosted-ci.yml`.

## Triggering

The workflow runs automatically for:

- pushes to `develop`;
- a manual `workflow_dispatch` run.

Pull requests targeting `develop`, `staging`, or `main` use the GitHub-hosted
workflow. This avoids running
untrusted fork code on a self-hosted machine.

It targets the standard runner labels:

```text
self-hosted, linux, x64
```

The runner must be registered in the repository or its organisation with those
labels. GitHub runner registration is an administrator action and requires a
short-lived registration token; do not store that token in the repository.

## Runner requirements

Install and keep current:

- Docker Engine with permission for the runner service account;
- Node.js 20+;
- pnpm 9+;
- uv and Python 3.12+;
- Git and Bash.

The workflow fails during its preflight step if any required command is absent.

## Security requirements

Use an ephemeral or dedicated runner. Pull request code executes on the runner,
so do not use a self-hosted machine that also contains production credentials,
unrelated repositories, or sensitive user data. The workflow requests only
`contents: read` and does not require repository secrets.

## What it validates

The workflow installs dependencies, checks the Panchang/client authority
boundary, runs Python lint/format/type checks and tests, runs the JavaScript
lint/format/type/test suite, and executes the development launch-readiness gate.
The workflow also runs the build contract and Docker image checks, dependency
and secret scans, disposable Postgres/Redis plus RLS checks, and an optional
Lighthouse audit. Set the repository variable `LIGHTHOUSE_URL`, or provide the
manual `lighthouse_url` input, to audit a deployed staging URL. Without a URL,
the workflow validates the Lighthouse budget file and records the audit as an
environment-gated skip.

The GitHub-hosted workflow runs the complete Python, TypeScript, PostGIS/Redis,
accuracy-harness, and aggregate checks for every pull request targeting
`develop`. It also validates promotion pull requests from `develop` into
`staging` or `main`.
