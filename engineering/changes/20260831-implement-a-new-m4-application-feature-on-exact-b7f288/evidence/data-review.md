# Data re-review — fix HEAD `4230dc8e73bcf4dfcf6c60d294d379d44a30c698`

## Binding and verdict

- Route: `b7f288f1e81e`
- Base SHA: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Prior failing HEAD: `cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06`
- Reviewed fix HEAD: `4230dc8e73bcf4dfcf6c60d294d379d44a30c698`
- Fix range: `cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06..4230dc8e73bcf4dfcf6c60d294d379d44a30c698`
- Supplied verifier result: PASS, fingerprint `0092b4cd8152eb7919c94c610e66c7a4d71ad46382f1c5db852df41af0ac8789`
- Review role: route-selected read-only `data_reviewer`
- Verdict: **FAIL**

The three prior findings are repaired for newly created supported state: failed runs with live reservations move to accounting recovery rather than retry, reconciliation now takes capacity before task/run locks, and migration 009 adds predicate-compatible task-history indexes. However, three Important data/recovery findings remain. No Critical finding was found.

## Findings

### Important — `FOR KEY SHARE` does not serialize authority revocation with accepted intake

Migration 009's security-definer authority functions select the matching observation/exception `FOR KEY SHARE` (`factory/src/adaptive_factory/resources/009_authority_audit_and_history_indexes.sql:32-60`). Intake invokes the function inside its insertion transaction after the source-identity advisory lock (`factory/src/adaptive_factory/store.py:254-262`). PostgreSQL non-key updates take a `FOR NO KEY UPDATE` row lock, which is compatible with `FOR KEY SHARE`; setting `revoked_at` is therefore not blocked by the supposed validation lock.

A deterministic PostgreSQL 17 probe paused intake immediately after `_verify_m0_authority()` returned true, updated and committed `revoked_at` on a second connection, then allowed intake to continue:

```text
authority_revocation_seconds=0.028
intake_result=[('accepted', '<task-id>')]
revoked_and_tasks=(True, 1)
thread_alive=False
```

The checked-in revocation test does not exercise this interleaving: it blocks intake on the source advisory lock and commits revocation before authority validation (`factory/tests/test_postgres_integration.py:165-179`). The implementation ledger's claim that authority rows are locked against concurrent revocation is therefore false, and an intake can commit after its authority has been revoked.

Required repair: use a row lock that conflicts with a `revoked_at` update (`FOR SHARE` or stronger), or require revocation and validation to use the same explicit advisory/row-lock protocol. Add a two-connection regression that pauses after successful validation, proves revocation cannot commit ahead of the intake linearization point, and then proves later intake fails.

### Important — migration 009 leaves pre-009 unresolved reservations claimable

The runtime repair correctly checks the failed current run for active reservations and moves it to `needs_human` with `accounting_blocked=true` (`factory/src/adaptive_factory/store.py:659-670`); completion also checks all task reservations and aggregate reserved counters (`factory/src/adaptive_factory/store.py:675-686`). Migration 009, however, contains no data validation/backfill for schema-008 tasks already left in `queued`/`retry` with an unresolved prior-run reservation (`factory/src/adaptive_factory/resources/009_authority_audit_and_history_indexes.sql:1-67`). Claim still admits any `queued`/`retry` task whose projection flag is false, without checking active reservations (`factory/src/adaptive_factory/store.py:481-484`).

A representative schema-008 database was seeded with exactly the state the prior implementation could commit: attempt 1 failed, its full reservation remained active, the task was `retry`, and `accounting_blocked=false`. After applying packaged migration 009, the normal runtime claim succeeded:

```text
legacy_reservation_post_009_grant=('<task-id>', 2)
task_row=('leased', False, 25000000, 1)
```

Completion will now fail later, but missing accounting did not block work or retry as required. This is an upgrade/restart safety defect in the forward-only migration path.

Required repair: in a forward migration, quarantine every nonterminal task with active reservations/aggregate disagreement before it is claimable, or add a database-backed `NOT EXISTS` reservation guard to claim plus a bounded reconciliation path. The migration must preserve immutable reservation/audit evidence and include a real 008 -> current upgrade regression with representative unresolved accounting.

### Important — exhausting a valid event budget prevents every supported lease-recovery path

The closed contract accepts `max_events` values from zero through 100,000 (`factory/src/adaptive_factory/contracts.py:174-196`). `_event()` raises once the persisted sequence reaches that limit (`factory/src/adaptive_factory/store.py:175-199`). Lease release, reconciliation and cancellation perform cleanup and then append a task event in the same transaction; event exhaustion rolls the whole transaction back (`factory/src/adaptive_factory/store.py:648-718,954-1004,1006-1024`).

The new checked-in boundary test explicitly accepts the stuck behavior after intake and claim consume a limit of two (`factory/tests/test_postgres_integration.py:716-733`). An independent probe then expired that lease and attempted all supported recovery paths:

```text
release   -> BudgetError: event budget exceeded
reconcile -> BudgetError: event budget exceeded
cancel    -> BudgetError: event budget exceeded
task_row=('leased', live_allocations=1, task_events=2)
```

The run, allocation and global/repository capacity remain live indefinitely; restart reconciliation cannot recover them. This violates bounded recovery and lets a valid intake limit permanently consume scheduler capacity.

Required repair: ensure safety cleanup cannot be rolled back by an exhausted business-event allowance. Options include reserving mandatory lifecycle capacity, enforcing a sufficient lower bound derived from the permitted lifecycle, or using a separate non-exhaustible bounded recovery/audit fact. Replace the test's expected stuck lease with successful capacity release and idempotent repeated recovery.

## Prior findings rechecked

### Repaired — cross-attempt accounting on newly executed failure paths

An active reservation on the failing current run now forces `needs_human` and `accounting_blocked`, and no retry claim is available. Completion checks every active task reservation plus cost/token/wall aggregate counters. The focused real-PostgreSQL regression and the full exit suite pass (`factory/tests/test_postgres_integration.py:772-797`). The remaining blocker is migration of already durable schema-008 state, described above.

### Repaired — reconcile/cancel lock order

Reconciliation now calls `capacity_lock_run()` before `SELECT ... tasks ... FOR UPDATE` (`factory/src/adaptive_factory/store.py:978-990`), matching cancel/supersede/release's capacity-before-task order. The two-connection regression completed cancel and reconciliation without `40P01`, timeout or double release (`factory/tests/test_postgres_integration.py:886-913`).

### Repaired — task-history index compatibility

Migration 009 adds valid/ready indexes for audit order, task/run usage, active reservations and expired-run lookup (`factory/src/adaptive_factory/resources/009_authority_audit_and_history_indexes.sql:25-30`). `audit_log_task_order` was selected with default planner settings in retained-history data; the usage/reservation/reconciliation indexes are predicate-compatible and selected by the checked-in plan-shape regression. The original missing-index defect no longer remains Important.

## Migration, roles, audit and recovery evidence

- Packaged migrations are contiguous `001..009`. Versions 001-008 retain their prior SHA-256 values; the applied and packaged migration-009 checksum matched `2e37378af506bf18ab11705430b6876136ac3918d3d1e5699e7d63848b946e6a`.
- A non-empty schema-008 upgrade applied only migration 009 atomically. A seeded legacy audit-v1 chain remained verifiable with `digest_version=1`; new audit rows use v2 and bind task, run and correlation identity (`factory/src/adaptive_factory/store.py:201-252,398-438`).
- Legacy M0 rows acquire null repository/policy bindings and therefore fail closed until explicitly reprovisioned. The new functions are `SECURITY DEFINER`, have fixed `search_path=pg_catalog,factory`, deny PUBLIC execute and grant runtime execute. Their lock strength remains the finding above.
- Runtime still cannot directly mutate capacity policy/allocation or update/delete audit, and the 20/10/1 capacity functions remain fixed-search-path capabilities.
- Migration 009 is additive and recovery documentation remains forward-only (`010+`) with preserved audit/backup comparison. The unresolved-reservation upgrade gap and event-exhaustion recovery gap prevent a PASS.

## Verification evidence

- `git diff --check cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06..4230dc8e73bcf4dfcf6c60d294d379d44a30c698` — PASS.
- `python3 factory/tests/run_disposable_exit.py` — PASS: 59/59 tests, effective roles, actual PostgreSQL restart, one repair, zero-repair replay, higher fence and late-holder rejection.
- Focused indexed-plan test — PASS; all four migration-009 indexes were valid and ready.
- Independent authority, 008 -> 009 unresolved-accounting, and exhausted-event recovery probes — FAIL as detailed above.
- The exact disposable container `adaptive-factory-data-rereview-4230dc8` and temporary environment were removed after review. No shared, Trust CI, external or production database was read or mutated.

No product file, commit or review receipt was changed. Only this report was overwritten.

**Final data-review result: FAIL for exact fix HEAD `4230dc8e73bcf4dfcf6c60d294d379d44a30c698`.**
