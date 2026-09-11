# Extract PR #12 lazy Trust CI CLI imports onto published 2.0.15

Change ID: `20260906-continue-published-2-0-15-to-next-final-stage-su-8e7fea`
Route: `8e7fea3efac6` (authority for this package; ignore later runtime overwrites)
Risk: low
Complexity: standard
Domains: generic
Write owner: `general_implementer`

## Problem

The user asked to read the change rules and continue the project to the final stage. This checkout is the already-merged path-aware branch at `7c61e3b` (VERSION **2.0.12**). The published product is `origin/main` `fd51dcfed6b33f4a8707c0db602328146df17cc9` (VERSION **2.0.15**, tag `v2.0.15`).

M0–M9 repository product, L5 landing, and the disabled pilot are already on `main`. Remaining unique product work starts with PR #12: human-approval CLI still eagerly imports FastAPI/worker/Postgres on current `cli.py`.

## Outcome

A human can run `python -m adaptive_trust_ci.cli --help`, `approval-create --help`, and `approval-submit` from a reviewed `origin/main`-based checkout without importing FastAPI, uvicorn, worker, PostgreSQL, or other server-only modules. Delivery is a **new open PR** to `main`. Merge, deploy, tag, M8/M9 activation, and live pilot stay human/blocked.

## Scope

### In scope

- New branch from `origin/main` `fd51dcfed6b33f4a8707c0db602328146df17cc9` (not this 2.0.12 checkout, not PR #28).
- Reconstruct PR #12 unique slice: command-local imports in `trust-ci/src/adaptive_trust_ci/cli.py`, new key-free `trust-ci/tests/test_cli.py`, operator section of `trust-ci/README.md`.
- Append-only `decisions.md` / `mistakes.md` notes for the CLI import pattern.
- Local verify + independent code/test reviews + open successor PR. Link PR #12 as source; do not close it.

### Out of scope

- Implementing on `fix/path-aware-shell-policy-circuit-breaker`.
- Using PR #28 as git parent or mixing its docs-sync.
- Wholesale cherry-pick/merge of `0f7f508`.
- PR #13 repository profiles, PR #15 investor demo.
- VERSION/tag/ZIP/GitHub Release, merge, deploy, live pilot, M8/M9 activation.
- Human approval keys, `.env`, deployed Trust CI policy/holdout/images/Postgres.
- GitHub Actions, root packaging markers, edits to `policy.py` / `api.py` / `worker.py` / models/signing/SQL.

## Constraints

- Backward compatibility: CLI flags, subcommand names, envelope JSON, `/approvals` unchanged. Only *when* modules load changes.
- Data/privacy: tests must not read/write human or runtime keys. No `Signer.generate()` in new CLI tests.
- Operational: no service restart, no policy digest change. Rollback is revert of the successor commit.
- Base SHA: `fd51dcfed6b33f4a8707c0db602328146df17cc9`.
- Dirty local `decisions.md` and `trust-ci/compose.yaml` (hardcoded 18080) must be discarded; main already has `${TRUST_CI_API_HOST_PORT:-18080}`.
