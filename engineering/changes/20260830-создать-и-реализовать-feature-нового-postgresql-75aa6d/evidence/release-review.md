# Release review — production-only promotion gate

- Route: `75aa6daa89b1`
- Reviewed tree fingerprint: `0e059501206c9ae185af36dac238d1576852a82328277e97edbf7896646d93e8`
- Base: `origin/main` (`1c06299894279a88b881defa3f19b004fa742223`)
- Reviewer: route-selected `release_reviewer` (independent; product code unchanged)
- Verdict: **PASS for PR/release-candidate delivery**

This verdict does not authorize merge or production deployment. Production remains **NO-GO** until the external conditions listed below are observed for the exact merged commit and immutable artifact.

## Findings

None blocking in the reviewed release scope.

## Acceptance and current-state review

- The implementation and current fingerprint-bound verification cover AC-001–AC-007: strict promotion contracts/signature checks, exact merged-SHA and artifact provenance, additive migration 004, atomic replay/idempotency and consume-once semantics, append-only terminal evidence, bounded observability, real PostgreSQL concurrency/restart/restore, and fail-closed denial paths.
- AC-008 is correctly split across trust boundaries. The repository prepares and tests `approval_rules: []`; only the deployed external policy, App-owned exact-SHA Check Run and branch protection can prove automated validation/PR/merge. The final production action remains separately gated by one `promotion:production` signature.
- `README.md`, `AGENTS.md`, `START_HERE.md`, `PROJECT_STATE.json`, Trust CI documentation and the change package consistently describe automated development delivery and one final production signature. `python3 -m unittest -v tests.test_structure` passed 11/11, including VERSION/README identity, the complete pairwise stack graph, external PR-only merge trust and absence of GitHub Actions.
- The route verification receipt is current and passing at the reviewed fingerprint with capability `trusted-host`; all selected profiles (`base`, `contracts`, `data`) and the `trust-ci-production-promotion` bundle passed.

## Rollout ordering and policy cutover

The executable order is safe and explicit:

1. Build and pin reviewed API/worker/runner/PostgreSQL artifacts and external holdout inputs by immutable digest; keep promotion/consumption disabled and production unchanged.
2. Back up the existing authority database, run the isolated administrator `role-bootstrap`, require exit 0, then apply checksum-locked migration 004. Compose enforces `postgres healthy -> role-bootstrap completed -> migrate completed -> API/worker`.
3. Deploy and prove the automated-only Trust CI epoch on a disposable PR. The production GitHub adapter verifies exact current `(context, app_id)`, installs and reads back `old+new`, then installs and reads back `new`. Failure restores and verifies `old+new`; no step removes all App-owned required checks.
4. Deliver and merge through the exact-SHA App-owned check with no human signature or chat approval. A live `needs_approval` is a failed/incomplete cutover, not a reason to request a legacy signature.
5. After merge, build/identify the immutable artifact and record its passed protected-branch attestation. Only then may the final production ceremony begin.

The checked-in example policy has `approval_rules: []`, retains all mandatory repository commands, holdout verification, immutable sandbox configuration and source-integrity checks, and limits promotion to `production` with a 900-second maximum TTL.

## Existing-volume migration and recovery

- Historical migration SQL is not rewritten. Migration 004 and its packaged resource mirror are checksum-locked, additive and forward-only.
- The prior D1 blocker is closed in the actual tree: `trust-ci/postgres/upgrade/004_deployer_role.sh` idempotently creates/repairs only `trust_ci_deployer` with constrained attributes and credential, while the migrator remains `NOCREATEROLE`. The Compose dependency makes the bootstrap a prerequisite rather than relying on fresh-volume init scripts.
- Current fingerprint evidence includes `postgres 003-to-004 role upgrade drill: PASS`, with a simulated pre-change role set, populated schema 003, two bootstrap executions and migration 004 verification.
- Current evidence also includes 33/33 real PostgreSQL tests, process/database restart PASS, integrity-checked custom backup and separate-database restore PASS, restored runtime-role access, and preserved single-use consumption/terminal state.
- Rollback is correctly forward-only for data: stop/kill-switch, restore the previous reviewed service image or apply migration 005+, retain promotion/nonce/consumption/audit history, and reconcile each consumed operation ID. Migration 004 is never edited or down-migrated.

## Observability and exact-SHA execution

- The API exposes bounded Prometheus series for promotion outcomes/reasons, dependency failures, accepted-unconsumed and consumed-without-terminal states, latencies, pending merge facts, reconciliation lag, validation outcomes and expired promotions. High-cardinality identifiers remain in durable audit/log data rather than labels.
- Release/runbook no-go signals include missing terminal evidence, stalled reconciliation, provenance mismatch, replay anomalies, audit failures, restore inconsistency and dependency outage. Production operators must bind these metrics to their external dashboards/pages before enabling promotion consumption.
- The prior clean-runner blocker is closed. The repository sandbox uses installed `python3`, read-only/no-network execution and no Docker socket; `GROK_VERIFY_CAPABILITY=repository-sandbox` excludes only trusted-host Docker orchestration. The clean-runner simulation passed without `.venv` or Docker access, while PostgreSQL/restart/restore/cutover evidence remains fingerprint-bound at the trusted-host boundary.
- The prior protected-evidence crash window is closed: durable exact-tuple get-or-insert precedes App success publication, retry recovers the original signed evidence identity, and completion is replayable without creating a second authority row.

## Single human gate

There is exactly one human signature in the target workflow: a fresh, short-lived `promotion:production` envelope created on a human-controlled machine after automated merge and exact artifact attestation, then verified, submitted once and atomically consumed immediately before the first production side effect. Verification, submission and consume do not add signatures. Legacy PR approval commands are inactive compatibility paths and must not be used to repair a failed policy cutover.

No human private key or signature was read, generated, requested, submitted or simulated during this review.

## Production no-go conditions / residual operational risk

Production remains NO-GO until external evidence proves all of the following for the exact release candidate:

- the implementation is committed, delivered by PR and merged under the App-owned exact-head check;
- the reviewed automated-only policy/holdout/images are deployed, and branch protection read-back shows the exact new context and GitHub App ID without an unprotected interval;
- role-bootstrap, migration 004, backup/restore and service health succeed against the intended deployment environment;
- the exact merged commit's immutable artifact digest appears in a passed protected-branch attestation;
- production dashboards/pages consume the new metrics, the kill switch is operational, and deployer reconciliation ownership is active;
- the human makes the sole final go/no-go decision and signs the exact production tuple within the 900-second TTL.

Any tuple/digest/policy mismatch, stale envelope, missing terminal evidence, dependency failure, failed cutover read-back or unavailable recovery path is a hard abort. No local receipt or this review substitutes for those external facts.

## Evidence inspected

- `.grok-stack/runtime/receipts/75aa6daa89b1/verification.json`: PASS at the reviewed fingerprint; all nine recorded checks passed, including the production-promotion bundle.
- Historical code/test/security/data review reports plus their closure reports, including the D1 existing-volume finding and the clean-runner/crash-window findings.
- Actual diff and surrounding implementation for Compose startup, migration/bootstrap, policy, runner boundary, promotion runbook, rollback and metrics.
- `python3 -m unittest -v tests.test_structure`: PASS, 11 tests.
- `git diff --check`: PASS.

No receipt, commit, push, pull request, merge, policy mutation, database mutation or deployment was performed by this reviewer.
