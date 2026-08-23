# P0 Trust CI control plane: PostgreSQL integration, GitHub App, deploy, branch protection

Change ID: `20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`
Created: 2026-08-23T17:39:00+00:00
Risk: medium
Complexity: high-risk
Domains: data, infra, frontend, integration
Route: `f771ecaf458d`
Branch: `feat/trust-ci-control-plane`
PR: draft `#2`

## Problem

Self-hosted Trust CI is implemented in-tree, but local baseline on HEAD `04348dbde391eaccb574c96740e2fa7b2fa9825a` is red, live PostgreSQL integration was skipped, no GitHub App exists, no webhook is registered, `main` is unprotected, and PR #2 has no App-owned policy-epoch check.

## Outcome

PR #2 stays draft until the deployed GitHub App publishes `adaptive-trust-ci/verified@<policy-sha12>` for the exact head SHA. Local suites and live PostgreSQL scenarios pass. Images, holdout and policy are digest-pinned. Branch protection, when applied, binds that exact check to the App ID. GitHub Actions remain absent.

## Scope

### In scope

- Reproduce and record the current baseline against HEAD `04348db`.
- Repair baseline regressions required for handoff step 1.
- Run disposable PostgreSQL integration and restart/recovery drills.
- Build and pin immutable API, worker, runner and holdout artifacts.
- Create/install the Trust CI GitHub App with Checks write, Contents read, Pull requests read.
- Deploy PostgreSQL, migrate, API, worker, runner image, holdout, HTTPS intake, backup and logs on this isolated host.
- Register HMAC webhook, prove the App-owned check, verify attestation offline.
- Apply app-bound branch protection only after the external check succeeds.
- Commit on `feat/trust-ci-control-plane` and update draft PR #2 with evidence.

### Out of scope

- GitHub Actions, Dependabot, or `.github/workflows/**`.
- Merging PR #2 unless the user explicitly orders it after reviewing external evidence.
- Replacing PostgreSQL with JSON/SQLite.
- Generating or handling a human approval private key.
- Changing deployed Trust CI policy/holdout/keys from inside a pull-request checkout once they exist.

## Constraints

- Backward compatibility: local hooks and delegated grants stay advisory.
- Data/privacy: no private keys, webhook secrets, or production env files in git.
- Operational: API cannot publish a successful check; worker-only App key; runner has no network or secrets.
- Human gate: `GROK_BUILD_HANDOFF.md` is the user-approved design and execution order. This change does not reopen product design.
