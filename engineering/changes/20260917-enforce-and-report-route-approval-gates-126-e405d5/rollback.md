# Rollback plan — Enforce and report route approval gates (#126)

## Trigger conditions

Contain the change if gate declarations can be removed or altered without detection, if a decision for one scope/resource satisfies another, if an existing grant or Trust CI evidence bypasses a declared gate, or if status reports a target as approved while required targets remain pending/rejected. A legitimate workflow blocked by a valid pending gate is resolved by recording the explicit scoped decision through the supported CLI, not by weakening enforcement.

## Application rollback

Revert the source change through a reviewed forward commit. Do not edit the deployed Trust CI service, branch protection, remote check runs, or approval stores; this change does not own those systems. Stop initiating new gated transitions/actions while the source revert is reviewed and checked. Preserve the active change package, gate decisions, review reports, and exact grant receipts for diagnosis; do not treat any of them as merge or external approval authority.

## Data recovery / forward-fix

There is no external data migration. The gate declaration, decision artifacts, and receipts are local package evidence. Preserve them when rolling back. If the issue is limited to incorrect status or binding, prefer a forward fix that keeps the gate fail-closed, binds route/change/gate/scope and exact action/resource as applicable, and continues to require the exact local grant. Do not auto-approve, broaden an existing decision, or reuse it across a changed scope. Any newly changed approval scope needs a new explicit decision.

## Verification after rollback

On the reverted source, verify the repository tests and local status command, then confirm the intended route/change remains identifiable and no protected action is in progress. Before a future protected action, re-evaluate the route's gates and obtain current exact grants; stale receipts do not authorize actions. For any pull request, verify the external App-owned Trust CI check and required signed approvals independently on the exact head SHA. Record whether the rollback was source-only and preserve the evidence package for re-review.
