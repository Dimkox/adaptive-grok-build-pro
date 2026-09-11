# Release plan — M4 Durable Factory Task Control Plane

## Delivery sequence

1. PR #10 M2 passes its App-owned exact-SHA check and merges or advances the stack.
2. PR #11 M3 passes `database` and `governance` approval scopes on its exact head and merges or advances the stack.
3. Regenerate the M4 route on that exact M3 head, create the isolated M4 branch/worktree, implement locally, and run disposable PostgreSQL evidence.
4. Update README/current-state/full stack graph, run one final verifier, perform all five independent reviews, record receipts, and open the stacked M4 PR.
5. Wait for the M4 App-owned exact-SHA Trust CI check and all separately required signed scopes. Do not merge, deploy, or publish as part of local completion.

## Staged rollout

Source delivery does not activate a service. A later approved staging rollout starts with kill enabled, checks migration status/backup, applies migrations under advisory lock, starts the Unix-socket API manually, verifies readiness, runs one synthetic intake/claim/heartbeat/release/restart/reconcile drill, and only then clears the switch.

## Metrics and alerts

Require intake/duplicate/reject counts, queue age, transitions, leases/reclaims/fence rejects, active capacity, reservations/usage/budget stops, retries/dead letters, supersession, kill state, reconciliation repairs/failures, and authorization failures. No secret, prompt, reasoning, raw body, or high-cardinality task identifier may appear in logs or metric labels.

## Go/no-go

Go requires exact accepted M3 base, green local verifier, real PostgreSQL exit evidence, five passing reviews/receipts, README parity, and the M4 App-owned exact-head check. Any missing approval, stale fingerprint, database-role breach, late-fence acceptance, unbounded accounting, Trust CI coupling, or external/execution capability is no-go.
