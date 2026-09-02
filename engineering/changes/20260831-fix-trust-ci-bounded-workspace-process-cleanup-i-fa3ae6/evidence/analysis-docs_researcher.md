# Documentation analysis — Trust CI zombie-only bounded-process cleanup

**Route:** `fa3ae6080deb`
**Change:** `20260831-fix-trust-ci-bounded-workspace-process-cleanup-i-fa3ae6`
**Scope:** read-only product analysis; this file is workflow evidence only.

## Outcome and contract to freeze

The affected primitive is `trust-ci/src/adaptive_trust_ci/workspace.py`:

- `_run_bounded_process()` returns an original bounded-command outcome (including the existing stdout-limit, stderr-limit, or timeout `WorkspaceError`) after it tries to terminate and reap its isolated process group.
- `_terminate_process()` currently treats any original process-group presence after `SIGKILL` as `WorkspaceError('bounded process group survived SIGKILL')`.
- The bugfix contract is deliberately narrower: a **verified zombie-only** remainder after `SIGKILL` must not replace/mask the original failure; any live member, failure to inspect process state, permission/identity ambiguity, own-group condition, or uncertain survivor must remain fail-closed.
- No public HTTP/OpenAPI, webhook, event payload, database schema, retry policy, Trust CI authority, external holdout, deployed policy, or runner image contract is changed. The existing OpenAPI contract at `engineering/contracts/openapi/trust-ci.v1.json` stays frozen; `contracts` arrays in the typed spec may stay empty if the completed spec explicitly records the unchanged contract boundary.

This is an internal execution/cleanup compatibility fix, not a relaxation of runner isolation. The worker/workspace/isolated-runner edges in `architecture/system.yaml` remain `no_network`; `EDGE-RUNNER-WORKSPACE` is explicitly fail-closed with zero retries, `SIG-RUNNER-FAILURE`, and terminal `reject`. `FIT-UNTRUSTED-RUNNER-NO-SECRETS` remains unchanged.

## Regression and evidence requirements

The historical M1 review evidence is the relevant root-cause trail: prior cleanup returned after a leader exit while a SIGTERM-ignoring same-group descendant remained; the old repair correctly added original-PGID tracking, TERM grace, KILL escalation, group disappearance, and leader reap. This hotfix must retain all of that behavior and add the missing post-KILL zombie distinction.

Required focused regression coverage:

1. A real child process group with a failure that has already been classified (at minimum a timeout; preserve existing stdout/stderr limit coverage) leaves only a reaped/zombie descendant after `SIGKILL`; the caller receives the original classified failure, not a cleanup-survivor error.
2. A live same-group descendant after `SIGKILL` remains a cleanup failure; it must not be normalized to success or to the original command error.
3. Any uncertain/uninspectable process state remains a cleanup failure. Do not infer “zombie” from `killpg(pgid, 0)` alone, because it reports zombie membership as existing.
4. Own-process-group refusal, invalid/nonexistent group race handling, leader reaping, stream closure, successful-command behavior, and the prior resistant-descendant overflow/timeout regressions remain green.
5. The regression test must be deterministic and clean up its own probe even if its assertion fails; do not leave a zombie/live helper process or depend on host-global process enumeration outside the spawned group.

Evidence should bind the test to the original exception category/message and the retained fail-closed behavior. The route requires base/contracts verification plus independent `code_review` and `test_review`; because this is product source, final `python3 scripts/grok_verify.py --mode pr` and receipts must use the final fingerprint. No PostgreSQL test, migration, or external operation is needed for this isolated workspace primitive.

## Change-package completion requirements

The active package is generated draft content and must be completed before local closure:

- `change-spec.yaml` is schema-v2 but has `UNKNOWN` objective metric/target and empty acceptance, invariant, forbidden-outcome, observability, and contract sections. Gate validation rejects `UNKNOWN` and requires at least one acceptance criterion with evidence. Use stable IDs and point acceptance evidence to the focused workspace regression plus final verification/review receipt.
- `requirements.md` must state the original-error-preservation condition and the live/uncertain-survivor fail-closed condition; it should list the zombie/leader/PGID race as failure cases.
- `architecture.md` should record that the change remains within `NODE-ISOLATED-RUNNER`/`NODE-EXACT-SHA-WORKSPACE` implementation ownership, changes no declared node/edge/data class/API, and preserves no-network/no-secret/read-only boundaries.
- `test-plan.md` should list the four P0 cases above and nearby legacy cleanup cases. Its automation section should name `trust-ci/tests/test_workspace.py`, applicable focused runner/workspace tests, root verification, and final review receipts.
- `release.md` should say source-only stacked Trust-CI bugfix: no deploy, policy/holdout/image change, runtime action, push, merge, or external write. Go requires the original failure to remain visible for zombie-only cleanup and live/uncertain survivors to fail closed.
- `rollback.md` should prescribe a single reviewed forward-fix/revert of the narrow workspace helper and regression. There is no migration or data recovery. A rollback must not restore the pre-existing behavior where a live descendant can survive, weaken `start_new_session`, group validation, `SIGTERM`/`SIGKILL`, reap, source-mutation detection, immutable/read-only runner, or no-network/no-secret guarantees.
- `tasks.md` should record reproduction/root cause, a failing regression before repair, focused checks, one final verifier, final route reviews/receipts, and PR/external exact-SHA gate as a separate merge requirement.

## Observability and operations

Existing low-cardinality durable metrics expose job state, attempts, expired leases, and kill-switch state; they do not expose per-command/process/PID fields, and must not gain high-cardinality job/repository/SHA/PID labels. `architecture/system.yaml` already maps runner failures to `SIG-RUNNER-FAILURE` and workspace preparation/access failures to `SIG-WORKSPACE-FAILURE`.

For this bugfix, sufficient observable behavior is a bounded/redacted Trust CI command failure that retains the original timeout/stdout/stderr classification for zombie-only cleanup, while an actual/uncertain survivor remains a clear fail-closed workspace/runner failure. Do not persist process listings, raw command output, environment, tokens, or PIDs as durable telemetry. A new Prometheus metric is not required unless implementation introduces a stable low-cardinality outcome counter; if it does, add metric rendering tests and avoid sensitive/high-cardinality labels.

The current Trust CI operational runbook remains applicable: the kill switch stops new jobs/approvals/claims without weakening branch protection, recovery retains PostgreSQL and attestations, and service rollback uses previous reviewed artifacts followed by a fresh exact-SHA check. This source-only slice does not authorize or require that operational sequence.

## Stacked delivery and README decision

- This branch is intentionally stacked on M2 base `9493741dd34fdfa1e37efdc09b35e30d5535be7c`. Keep the diff Trust-CI-only (`trust-ci/src/adaptive_trust_ci/workspace.py` and its focused tests, plus active-package evidence/documentation as needed); do not alter architecture authority/digests unless the actual declared M2 model changes.
- The route selects `general_implementer` as the sole writer and code/test reviewers after final verification. Local results remain advisory; PR merge still requires the deployed App-owned `adaptive-trust-ci/verified@<policy-sha12>` check on the exact final head SHA and any required external approvals.
- **README change is not required for this narrow bugfix.** The root README already accurately describes the same existing Trust CI isolated/no-network/read-only runner and changes no component, version, map node/edge, public contract, or operational command. Update it only if the final implementation changes a user-facing/current-state claim; otherwise avoid churn. If changed for release, preserve VERSION identity and the complete K16 `---` graph.

No primary upstream sources were needed; repository-local contracts, M2 architecture, Trust CI documentation, current workspace code/tests, and historical review evidence are sufficient.
