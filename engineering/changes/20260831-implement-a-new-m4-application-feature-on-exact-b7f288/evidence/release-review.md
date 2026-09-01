# Final independent release review — M4 durable factory control plane

## Verdict and binding

**FAIL — Important forward-recovery finding present.**

- Route: `b7f288f1e81e`
- Base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Prior reviewed head: `4230dc8e73bcf4dfcf6c60d294d379d44a30c698`
- Reviewed product head: `83e6b0d0c29e813932aa29b0d72ac4d85d27df7b`
- Focused range: `4230dc8e73bcf4dfcf6c60d294d379d44a30c698..83e6b0d0c29e813932aa29b0d72ac4d85d27df7b`
- Exact-head local verification receipt: PASS, fingerprint `9a9dd64921cc5edf8889330b79732016c0235cc37e4a27c712a05128b3659746`, including `factory-postgres-exit=pass` and source stability PASS.

I reviewed the focused and full M4 ranges, prior release finding closure, migration 010, store readiness/claim/release/accounting paths, schema-008 upgrade test, installer inventory, bootstrap/Compose configuration, README/release/rollback guidance, cleanup semantics, active route/state, and exact-head verification evidence. `git diff --check` over the focused range is clean.

## Important finding

### RR-002 — Migration 010 leaves a valid schema-008 blocked-accounting state permanently non-ready instead of quarantining it

Migration 010 quarantines `queued`/`retry` tasks only when they have an active reservation or nonzero reserved aggregates (`factory/src/adaptive_factory/resources/010_authority_accounting_and_cleanup.sql:41-70`). It does **not** include `task.accounting_blocked=true` in either predicate.

That is a reachable schema-008 state with zero active reservations and zero aggregates: missing-price/usage handling sets `accounting_blocked=true` (`factory/src/adaptive_factory/store.py:840-973`), then a subsequent retryable release with no reservation keeps the task's target as `retry` because the pre-010 release path only changes target for an active reservation (`4230dc8:factory/src/adaptive_factory/store.py:670-718`). The task will therefore enter migration 010 as `retry`, `accounting_blocked=true`, and otherwise zeroed.

After upgrade, it remains `retry`. The new readiness gate correctly detects the inconsistency and returns not-ready (`factory/src/adaptive_factory/store.py:80-93`), and claim correctly refuses it (`:513-520`), but no supported recovery path changes the task to `needs_human` or clears the inconsistency. This leaves a legitimate schema-008 upgrade permanently unable to pass the documented readiness gate. The checked-in upgrade regression covers only an unresolved reservation/nonzero aggregate (`factory/tests/test_postgres_integration.py:984-1098`), so it cannot establish closure for this state.

Impact: a separately approved local rollout from an eligible older durable state can become stuck before activation despite migration 010’s stated legacy-accounting quarantine and the release plan’s claimable-accounting go/no-go gate. Manual direct database mutation would be an undocumented security-sensitive recovery operation, contrary to the bounded forward-recovery plan.

Required repair: extend migration 010 (or add reviewed forward migration 011) to quarantine every nonterminal claimable state whose accounting is blocked or inconsistent, including zero-reservation/zero-aggregate `accounting_blocked` rows. Preserve task/run/audit facts, provide an observable quarantine count or bounded operator disposition, and add a real schema-008-to-current regression that constructs this exact state and proves: migration completes, task becomes `needs_human`, readiness passes, claim remains impossible, and recovery is explicit/idempotent. Re-run exact-tree verification and all route-selected reviews after the repair.

## Controls assessed as sound

- The owner/runtime bootstrap closure remains sound: `adaptive-factory-admin bootstrap-local` applies checksum migrations with the owner DSN, provisions a bounded `NOINHERIT` runtime login with only `factory_runtime`, and verifies effective-role readiness with the runtime DSN. Compose/environment examples and installer inventory remain consistent.
- Migration 010 changes authority row locks from `FOR KEY SHARE` to `FOR SHARE`, which serializes the non-key `revoked_at` update against intake. The committed integration tests cover both authority forms and the after-validation revocation interleaving.
- Mandatory cleanup facts are separated from the ordinary event budget, preserving release/reconcile/cancel capacity cleanup under exhausted ordinary events. The bounded/idempotent cleanup tests cover this behavior.
- The source remains local-only: UDS rather than TCP, no provider/shell/repository/GitHub/systemd/deploy/Trust-CI mutation path, and Docker limited to disposable test execution. Migration recovery remains forward-only; documentation consistently calls for schema 010 and forward migration `011+` after durable intake.
- The README truthfully calls M4 a local source candidate and keeps final reviews, PR delivery, exact-head App check, signed scopes, merge, and deployment pending. The active change is `verifying`, not complete.

## Delivery boundary

The exact-head local verifier PASS is useful preflight evidence but does not waive RR-002 and is not merge authority. This report authorizes no migration, activation, PR delivery, merge, tag, release, deployment, production mutation, or Trust CI action.

After RR-002 is closed and the evidence tree is frozen, local closure requires a fresh fingerprint-bound verifier and all route-selected reviews on that same tree. Merge eligibility still requires the GitHub App-owned `adaptive-trust-ci/verified@<policy-sha12>` Check Run plus every required independently signed scope on the exact PR head.
