# Rollback plan — production-only human approvals

## Trigger conditions

Any incorrect acceptance/consumption, provenance mismatch, replay, missing audit, role escape, dependency/reconciliation failure, restore inconsistency, wrong Check Run owner/context or absent automatic gate.

## Application rollback

Before the final ceremony, abandon or revise the unmerged stack; production and old policy are unchanged. During the ceremony, failure before consume aborts all remaining steps. After consume, activate the kill switch, reconcile the unique operation ID, and restore the reviewed prior image/data path; do not activate the new policy unless deployment is proven successful.

If the new policy was activated, restore the old PR-approval policy, prove its App-owned exact check on a disposable PR, then restore the required context without an unprotected interval.

## Data recovery / forward-fix

Retain migration 004 and every evidence, nonce, consumption and audit row. Never down-migrate or edit applied SQL; forward-fix with migration 005+ and reconcile operation IDs against external deployment history after restore.

## Verification after rollback

Verify deny state, exact App identity/context, automatic positive/negative checks, preserved uniqueness/audit, external operation reconciliation, healthy alerts and rejection of every stale envelope. Re-enable only through a new final production ceremony if the previous consume was terminal.

The plan binds each implementation task to its rollback evidence and preserves the forward-only migration/consume history: `docs/superpowers/plans/2026-08-30-production-only-human-approvals.md`.
