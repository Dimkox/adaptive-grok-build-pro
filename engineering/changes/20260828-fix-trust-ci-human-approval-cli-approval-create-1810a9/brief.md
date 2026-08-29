# Fix Trust CI human approval CLI: approval-create and approval-submit must run from a source checkout on a human-controlled host without importing API, worker, PostgreSQL, or other server-only dependencies; add regression tests and reproducible operator setup documentation without weakening signature verification or exposing private keys

Change ID: `20260828-fix-trust-ci-human-approval-cli-approval-create-1810a9`
Created: 2026-08-28T23:17:12+00:00
Risk: medium
Complexity: standard
Domains: data, api

## Problem

The documented human approval command is unavailable on the deployment host. The
console script is not installed, and the documented source-checkout fallback fails
before argument parsing because `adaptive_trust_ci.cli` imports FastAPI, psycopg,
the worker and the server store unconditionally. The host has the approval command's
cryptographic dependency but intentionally does not have the server dependency set.

## Outcome

An operator can invoke `approval-create` and `approval-submit` from a reviewed source
checkout on a human-controlled host without installing or importing server-only
components. Existing exact-SHA, policy-epoch, TTL, scope, signature and replay checks
remain unchanged.

## Scope

### In scope

- Reproduce the import-time failure under an environment without server dependencies.
- Lazily load command-specific dependencies in the Trust CI CLI.
- Add regression coverage for human-command parsing and approval creation when
  FastAPI, psycopg and uvicorn are unavailable.
- Document a reproducible source-checkout invocation and dependency preflight.

### Out of scope

- Generating, reading, copying or submitting a human private key or approval.
- Changing `/approvals`, approval payloads, signature verification or trust-store data.
- Changing deployed policy, holdout, images, PostgreSQL state or branch protection.
- Auto-approvals, bypasses, reduced approval scopes or deployment of this hotfix.

## Constraints

- Backward compatibility: existing `adaptive-trust-ci` command names and arguments stay stable.
- Data/privacy: the private key remains outside the repository, API, worker and agent environment.
- Performance: no server runtime-path change; human commands avoid unrelated imports.
- Operational: delivery is a separate PR; a human still performs the signing step.
