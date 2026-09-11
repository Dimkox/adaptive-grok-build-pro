# Architecture — lazy Trust CI CLI imports on 2.0.15

## Current behavior

`origin/main` `trust-ci/src/adaptive_trust_ci/cli.py` is byte-identical to PR #12's merge-base `1c062998`. It imports `api`, `backup`, `github`, `github_app`, `holdout`, `migrations`, `models`, `policy`, `settings`, `signing`, `store`, `worker` at module import time. `--help` and human commands fail with `ModuleNotFoundError: fastapi` on a signing-only host.

## Proposed behavior

Stdlib-only module scope. Product imports live inside the selected command branch and `_doctor()`. `approval-submit` stays stdlib. `approval-create` imports only `Policy`, `ApprovalPayload`, `Signer`, `sign_approval`. Command names, flags, JSON, `0600` envelope mode, `/approvals` POST, and User-Agent `adaptive-trust-ci-human/2.1.0` stay frozen.

## Components and boundaries

| Family | Imports allowed |
| --- | --- |
| parser / `--help` / `approval-submit` | stdlib only |
| `approval-create` | models / policy / signing |
| verify / keygen / trust-store-validate | models / policy / signing as already used |
| `api` | uvicorn, create_app, ApiSettings |
| `worker` | Worker, signals, WorkerSettings |
| migrate / migration-status | PostgresMigrator, CommonSettings |
| policy-digest | Policy, CommonSettings |
| holdout-digest | bundle_digest only |
| branch-protect | GitHubClient, Policy |
| backup / restore / prune | backup (+ CommonSettings where used) |
| kill-switch | utc_now, CommonSettings |
| doctor | current doctor graph, lazy |

Must not change: `policy.py`, `models.py`, `signing.py`, holdout bundle, API/worker/store/runner/workspace, SQL, VERSION, `trust-ci/pyproject.toml`, GitHub Actions, root packaging.

## Data flow

Unchanged. Human create signs locally; submit POSTs opaque bytes. Server commands still do the same work after dispatch.

## API and event contracts

No contract change. Envelope schema v1 and `/approvals` stay identical. Later attestation metadata (`spec_digest`, `criterion_coverage`) unused by this slice.

## Decisions

1. Base: `origin/main` `fd51dcf`. Not this checkout. Not PR #28.
2. Reconstruct unique files from PR #12; do not cherry-pick `0f7f508`.
3. New CLI tests are key-free. Do not port `Signer.generate()` from PR #12. Envelope contract stays in existing `test_signing.py`.
4. Leave PR #28 independent (docs-only, already App-green).
5. Preserve later main path/policy/holdout/workspace/runner hardening by not touching those files.

## Risks and mitigations

- Wholesale cherry-pick restores stale evidence → reconstruct three product files + log appends.
- Missed lazy import for a server command → freeze 19-command inventory + fake-module cases.
- Key material in new tests → mock `approval-create` / `keygen`; no PEM.
- Stacking on PR #28 → independent PR from `fd51dcf`.
