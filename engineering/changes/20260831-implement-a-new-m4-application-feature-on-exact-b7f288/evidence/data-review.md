# Data review — exact head `cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06`

## Binding and verdict

- Route: `b7f288f1e81e`
- Base SHA: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Reviewed product HEAD: `cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06`
- Reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06`
- Review role: route-selected read-only `data_reviewer`
- Verdict: **FAIL**

Three Important data findings remain. No Critical finding was found. The product persistence code is unchanged from previously reviewed product commit `f82134d`; the later commits alter verifier behavior/tests and evidence, so this review re-ran the final PostgreSQL suite and independently probed uncovered transactional/accounting paths on the exact requested HEAD.

## Findings

### Important — a task can complete with an unresolved reservation from an earlier attempt

Failure release closes the attempt, run and capacity allocation but neither settles nor invalidates that run's live budget reservations (`factory/src/adaptive_factory/store.py:629-657`). Usage settlement only releases reservations for the current `(task_id, run_id)` (`factory/src/adaptive_factory/store.py:811-825`), and completion checks only for current-run reservations rather than all unresolved task reservations or the task aggregate reserved counters (`factory/src/adaptive_factory/store.py:636-647`). Therefore a worker can reserve the full task budget, fail as `worker_lost`, retry, record a zero-cost observation on the second run and complete successfully while the first reservation remains live.

A fresh PostgreSQL 17.11 probe on the reviewed tree produced:

```text
cross_attempt_terminal=ready_for_human
task_row=('ready_for_human', cost_reserved_micros=25000000,
          tokens_reserved=2000000, wall_reserved_seconds=14400,
          live_reservations=1)
```

This violates AC-007's fail-closed missing-accounting rule and the documented requirement that completion have settled accounting. It also leaves the immutable reservation and mutable task aggregates disagreeing with terminal meaning.

Required repair: define and enforce one durable cross-attempt accounting policy. At minimum, any unresolved reservation from any task run must prevent `ready_for_human`; lost-run reservations must be reconciled through trusted usage evidence or move the task to an explicit accounting-blocked/manual-recovery state. Add a real-PostgreSQL regression covering reserve -> infrastructure failure -> retry -> attempted completion and verify reservation/aggregate agreement.

### Important — reconciliation reverses the capacity/task lock order and deadlocks with cancellation

The common lease-close paths lock capacity counters before locking task/run rows (`factory/src/adaptive_factory/store.py:523-554`, with the database locks in `factory/src/adaptive_factory/resources/007_capacity_authority.sql:56-77,127-157`). Reconciliation first locks the task row at `factory/src/adaptive_factory/store.py:940-943`, then calls `_release_locked()`, which tries to lock capacity at `factory/src/adaptive_factory/store.py:626-628`. This is the reverse order for the same live lease.

A deterministic two-connection PostgreSQL probe held the reconciliation task lock, let cancellation acquire the capacity locks, and then allowed both supported paths to continue. PostgreSQL reported:

```text
lock_order_results=[('reconcile', 1)]
errors=[('cancel', 'DeadlockDetected', 'deadlock detected')]
threads_alive=(False, False)
```

The database preserves atomicity by aborting cancellation, but the requested fixed lock order and concurrent restart-safe control behavior are not satisfied; there is no store-level retry for the aborted command.

Required repair: make claim, cancel, supersede, release and both reconciliation branches acquire capacity/task/run locks in one documented global order, and add a two-connection regression that runs reconcile concurrently with cancel/supersede without `40P01`, timeout or double release. If deadlock/serialization retry remains part of the design, implement a bounded retry at the command boundary with the same idempotency key rather than relying on callers.

### Important — hot task-history queries have no predicate-compatible indexes

The schema creates no task-scoped index for `audit_log`, `usage_observations`, or active `budget_reservations` (`factory/src/adaptive_factory/resources/001_initial.sql:85-98`, `factory/src/adaptive_factory/resources/003_budgets_kills_reconciliation.sql:1-25`). Migration 005 adds only task-list and run-reconciliation indexes (`factory/src/adaptive_factory/resources/005_security_accounting_commands.sql:55-56`). Yet the store repeatedly queries:

- audit by `task_id ORDER BY audit_id LIMIT 100001` (`factory/src/adaptive_factory/store.py:376-408`);
- reservations by `(task_id, run_id, released_at IS NULL)` (`factory/src/adaptive_factory/store.py:811-825`);
- cumulative output usage by `task_id` on every new observation (`factory/src/adaptive_factory/store.py:826-839`).

Fresh-database `EXPLAIN (COSTS OFF)` showed sequential scans plus an audit sort for all three predicates. PostgreSQL does not automatically index referencing foreign-key columns. At the allowed 100,000 events per task and multiple retained tasks/runs, the audit verification and accounting mutation cost grows with global retained history, not the selected task. The five-second timeout bounds damage but converts valid operations/recovery checks into timeouts; it does not make their query work bounded. This also contradicts the frozen data architecture's explicit task-id reservation/usage index requirement and representative-plan gate (`evidence/analysis-data_architect.md:53-62`).

Required repair: add a forward migration `009+` with predicate/order-compatible indexes, at least `audit_log(task_id, audit_id)`, a task/run index for usage observations, and a partial active-reservation index on `(task_id, run_id) WHERE released_at IS NULL`. Record `EXPLAIN (ANALYZE, BUFFERS)` at representative retained volumes for claim, accounting, audit verification and reconciliation before acceptance.

## Rechecked controls that pass

- Packaged migrations are contiguous `001..008`; applied version/name/SHA-256 rows exactly matched packaged bytes on a fresh database. `plan_migrations()` rejects gaps, missing packaged history, renamed files and checksum drift, and `apply()` serializes the registry plus all pending DDL under one factory advisory transaction (`factory/src/adaptive_factory/migrations.py:33-108`).
- The migrations remain factory-only and forward-only. Recovery documentation correctly prohibits down-migration after durable intake and requires preserved evidence plus migration `009+` (`engineering/changes/20260831-implement-a-new-m4-application-feature-on-exact-b7f288/rollback.md:1-5`).
- Runtime cannot directly insert/update capacity counters, insert/update allocations, update intake identities, or update/delete audit; schema `trust_ci` usage is denied. Canonical 20/10/1 ceilings, security-definer fixed-search-path capacity functions and live-allocation fencing remain effective (`factory/src/adaptive_factory/resources/005_security_accounting_commands.sql:58-71`, `006_runtime_policy_privileges.sql:1-2`, `007_capacity_authority.sql:1-169`, `008_allocation_release_authority.sql:1`).
- Claims use `FOR UPDATE SKIP LOCKED`, per-task fences are monotonic, capacity allocation/release is transactional, and stale/hidden allocations fail worker fencing and readiness. The finding above is specifically the inconsistent reconciliation lock order, not a capacity arithmetic failure.
- Retry classification remains closed to the four infrastructure classes and attempt three becomes `dead`; event/output/cost/token ceilings, command replay binding, audit hashing and bounded reconciliation page/timeout checks are present. The cross-attempt reservation lifecycle is the unresolved accounting exception.

## Verification evidence

- `git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06` — PASS.
- `python3 factory/tests/run_disposable_exit.py` — PASS: 43/43 tests, effective-role checks, actual PostgreSQL restart, one repair, zero-repair replay, higher fence and late-holder rejection.
- Independent PostgreSQL 17.11 probes — FAIL as detailed above for cross-attempt accounting and reconcile/cancel lock order.
- Query-plan probes — sequential scans for task audit, task usage aggregation and active run reservation aggregation; audit also sorts by `audit_id`.
- Migration registry — exact packaged/applied checksums matched for all eight versions.

The exact disposable review container `adaptive-factory-data-review-cf0219` was removed after the probes. The disposable test runner also removed its own generated container. No shared, Trust CI, external or production database was read or mutated; no product file or review receipt was changed.

**Final data-review result: FAIL for exact product HEAD `cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06`.**
