# Release plan — Enforce and report route approval gates (#126)

## Deployment

This is a source/workflow change. Deliver it through the normal reviewed branch and pull-request path. It does not deploy policy or mutate remote Trust CI, branch protection, credentials, production state, or external systems. Operators adopting the change should upgrade the local repository tooling as one unit: gate declaration persistence, decision CLI/status, workflow enforcement, and grant enforcement must come from the same reviewed source revision.

At change start, the route's `human_gates` declaration is captured in the package state and bound to its route ID. Before using the new behavior, inspect the gate declaration and the approved scope files in the active package. The gate record is local workflow evidence and its `--actor` value is not authenticated identity. Keep the independently required exact delegated local grant and external Trust CI approval/check procedures unchanged.

## Feature flags / staged rollout

There is no bypass flag or automatic migration that approves existing gates. All declared gates start pending until an explicit decision is recorded for the active route/change/scope. A missing, rejected, stale, malformed, or mismatched decision blocks its applicable transition or action. The operator may first inspect with `python3 scripts/grok_gate.py status`, then record a scoped decision with `python3 scripts/grok_gate.py decide ...` using the package's exact gate name and any required action/resource arguments.

`scope_and_design_approval` is required before `scoped → approved`. `migration_or_external_write_approval` is required for the exact recorded migration or external-write plan and is checked again when the matching grant is created and consumed. `production_action_approval` is checked before production grant creation and again at use. For every operation, the exact delegated grant remains independently required. Local gate decisions, grants, and receipts do not satisfy Trust CI's signed approval scopes or exact-head App-owned check.

## Metrics and alerts

Use `grok_status.py` to inspect every declared gate, its state, and its binding. Investigate any pending, stale, invalid, or mismatched gate before attempting the protected transition/action. Treat an aggregate target-specific migration/external-write gate as approved only when all required targets are approved. Gate state is not evidence of remote deployment or merge eligibility.

## Go/no-go criteria

Proceed with local adoption only when the active route declaration matches the persisted package binding; each gate applicable to the requested transition/action is explicitly approved for the current scope and exact target; and the separate required grant is valid for the exact action/resource and current tree. Stop on any declaration mismatch or incomplete target approval. For merge, independently require the external Trust CI check and all configured signed approval scopes on the exact PR head. No operational production or external write is implied by adopting this source change.
