# Data review — M4 durable control plane

## Binding and verdict

- Route: `b7f288f1e81e`
- Base SHA: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Reviewed head SHA: `01643c6594947535e690c5722f710081c9b9db9f`
- Reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..01643c6594947535e690c5722f710081c9b9db9f`
- Role: route-selected read-only `data_reviewer`
- Verdict: **FAIL**

Three Important findings violate the declared capacity/reconciliation, budget/idempotency, and immutable-record invariants. Under the requested gate, any Critical or Important issue is a failure.

## Findings

### Important — cancelling or superseding a leased task permanently leaks capacity and makes reconciliation fail

`intake()` supersedes every nonterminal generation, including `leased`, by clearing the task's current run/fence without releasing its run or capacity allocation and without decrementing either capacity counter (`factory/src/adaptive_factory/store.py:157-179`). `cancel()` similarly changes a leased task to `cancelled` without releasing the run/allocation/counters (`factory/src/adaptive_factory/store.py:689-701`). The normal release path is the only code that releases the allocation and decrements counters (`factory/src/adaptive_factory/store.py:454-490`).

The leaked run is not self-healing. Reconciliation selects every expired unreleased run (`factory/src/adaptive_factory/store.py:652-677`), but `_lock_grant()` requires the task to still have the same current run/fence and state `leased` (`factory/src/adaptive_factory/store.py:424-439`). A cancelled task fails the state predicate; a superseded task also has null current run/fence. The resulting `FenceError` rolls back the single transaction for the whole reconciliation page, so one leaked row can prevent unrelated expired leases from being repaired. This contradicts AC-002, AC-005, AC-009 and the explicit requirement that cancellation/supersession/reconciliation preserve evidence and be idempotent (`engineering/changes/20260831-implement-a-new-m4-application-feature-on-exact-b7f288/requirements.md:6-13,22`).

Disposable PostgreSQL 17 evidence:

```text
after_cancel= ('cancelled', 'leased', None, None, 1)
reconcile_error= FenceError stale or expired fence
counter_after_reconcile= 1
live_allocations_after_reconcile= 1
after_supersede= ('superseded', 'leased', None, 1)
```

Required repair: make terminal/superseding transitions and lease release one locked, idempotent transaction with a single fixed lock order; or explicitly mark an active run released/expired, release its allocation, and decrement all applicable counters before clearing the task pointer. Reconciliation must isolate or durably classify a bad candidate rather than roll back every candidate in the page. Add concurrent PostgreSQL tests for cancel-while-leased, supersede-while-leased, repeat commands, and a page containing both a stale inconsistent row and a valid expired lease.

### Important — reservation, observation, wall, and retry-idempotency rules do not enforce the declared budgets

`reserve_budget()` checks `reserved + observed + requested` before inserting, but `observe_usage()` checks only previously observed amounts and ignores existing reservations (`factory/src/adaptive_factory/store.py:512-547,549-615`). Therefore a task can reserve the full cost/token ceiling and then record the full ceiling again, leaving durable totals at twice the declared limit. Reservations are never consumed/released and their amounts are never reconciled to observations. The persisted `wall_seconds` has only a nonnegative constraint (`factory/src/adaptive_factory/resources/003_budgets_kills_reconciliation.sql:1-12`) and is never compared with the task deadline or wall budget, so `999999` seconds is accepted for a task whose maximum wall time is 14,400 seconds.

The reservation operation is also not retry-idempotent: it performs the budget-exceeded check before `ON CONFLICT(idempotency_key) DO NOTHING`, so replaying the exact successful full-budget command raises `BudgetError` rather than returning the original result (`factory/src/adaptive_factory/store.py:523-547`). If a conflict occurs while capacity remains, it returns a newly generated, non-persisted reservation UUID rather than selecting the existing reservation. This contradicts AC-007 and the API-wide idempotency requirement (`engineering/changes/20260831-implement-a-new-m4-application-feature-on-exact-b7f288/requirements.md:11,14,22`).

Disposable PostgreSQL 17 evidence:

```text
duplicate_reservation= BudgetError budget exceeded or accounting blocked
budget_totals= (25000000, 25000000, 25000000, 2000000, 2000000, 2000000) usage_created= True
reserved_wall_seconds= 999999
```

Required repair: define and enforce one transactional accounting invariant (for example outstanding reservation plus settled usage never exceeds each task limit), consume/release reservations when usage is observed, enforce wall/output/event dimensions consistently, and resolve an idempotency key before applying a new-command budget check. A duplicate must validate command equivalence and return the persisted identifier/result. Add PostgreSQL tests that query durable aggregate invariants after retries and concurrent reserve/observe operations.

### Important — PostgreSQL does not enforce the documented immutability boundary

The architecture declares immutable intent/run/attempt/event/audit records (`engineering/changes/20260831-implement-a-new-m4-application-feature-on-exact-b7f288/architecture.md:9-21`), but migration 003 grants the runtime role unrestricted table-level `UPDATE` on `accepted_intents`, `task_events`, `runs`, and `attempts` (`factory/src/adaptive_factory/resources/003_budgets_kills_reconciliation.sql:48-54`). There are no immutable-column grants or triggers. As a result, the same role trusted to run the product can rewrite frozen intake bodies/digests and event identity/evidence, or alter run/attempt identity and fencing columns outside store invariants. The integration privilege test checks only that `audit_log` lacks UPDATE/DELETE (`factory/tests/test_postgres_integration.py:266-287`) and misses the other records.

Disposable PostgreSQL 17 evidence (the update was rolled back):

```text
runtime_update_privileges= (True, True, True, True)
immutable_intent_update_rows= 1
```

Required repair: grant only the lifecycle columns that must change, keep accepted intents and task events insert/select-only, and enforce immutable identity/fence/evidence columns at the database boundary. Extend the role test to attempt forbidden mutations under `SET LOCAL ROLE factory_runtime`, not merely inspect `audit_log` privileges.

### Minor — cross-record task/run consistency is not constrained in the schema

`capacity_allocations` independently references `run_id` and `task_id` (`factory/src/adaptive_factory/resources/002_runs_leases_capacity.sql:45-53`), while `budget_reservations` and `usage_observations` independently reference those identifiers (`factory/src/adaptive_factory/resources/003_budgets_kills_reconciliation.sql:1-25`). None uses the available composite run identity `(run_id, task_id)`. A runtime insert can therefore associate a valid run with a different valid task while satisfying every foreign key, corrupting capacity/accounting attribution. `audit_log.run_id` has no foreign key at all (`factory/src/adaptive_factory/resources/001_initial.sql:85-97`). Use composite foreign keys where a record is task-and-run scoped, and document whether audit intentionally permits run IDs not yet present.

### Minor — index/query-plan evidence does not cover the bounded production query shapes

The checked-in PostgreSQL tests exercise correctness on tens of rows but contain no seeded-volume `EXPLAIN`/`EXPLAIN ANALYZE` evidence. In particular, repository-filtered listing orders by `task_id` (`factory/src/adaptive_factory/store.py:260-276`) while `tasks_list` is `(repository_id, created_at, task_id)` (`factory/src/adaptive_factory/resources/001_initial.sql:63-65`), and reconciliation filters by expiry but orders/keysets by `task_id` (`factory/src/adaptive_factory/store.py:652-662`) while `runs_expiry` begins with `lease_expires_at` (`factory/src/adaptive_factory/resources/002_runs_leases_capacity.sql:21-22`). Provide volume/distribution assumptions and plans for claim, list, audit verification, kill lookup, and reconciliation; add indexes matching the selected keyset semantics if plans show sorts or broad scans.

## Positive observations

- Migrations are contiguous, checksum-bound, run under a transaction-scoped advisory lock, and set bounded migration lock/statement timeouts (`factory/src/adaptive_factory/migrations.py:33-64,84-108`). The forward-only recovery approach is documented; no destructive down-migration is introduced.
- Claim locks capacity counters in sorted order before `FOR UPDATE SKIP LOCKED`, increments a per-task fence transactionally, and binds subsequent worker mutations to task/run/owner/fence/packet/state/lease/deadline (`factory/src/adaptive_factory/store.py:320-439`). The focused clean-path concurrency/fencing tests passed.
- The audit log is denied UPDATE/DELETE for `factory_runtime`, serializes the per-task head, and verification recomputes the bounded chain (`factory/src/adaptive_factory/store.py:89-136,278-310`). This positive property does not compensate for mutable accepted intents/events or the release blockers above.

## Commands and evidence

Static binding and inspection:

```text
git rev-parse HEAD
# 01643c6594947535e690c5722f710081c9b9db9f
git rev-parse 67714a1f1b87effcfabe55d5ca2770d0a68d17c1
git diff --name-status 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..01643c6594947535e690c5722f710081c9b9db9f
git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..01643c6594947535e690c5722f710081c9b9db9f
# exit 0
```

Disposable database baseline:

```text
docker run --name m4-data-review-b7f288 ... postgres:17-alpine
FACTORY_TEST_DATABASE_URL=<disposable-local-url> uv run --project factory --with-editable factory python -m unittest factory.tests.test_postgres_integration -v
# Ran 5 tests in 6.715s — OK
```

Targeted probes used the public service/store methods plus read-only SQL assertions against the same fresh database. Their exact outputs are quoted under each finding. The immutable-role mutation was enclosed in a transaction and rolled back. The exact disposable container `m4-data-review-b7f288` was removed after review; no shared, Trust CI, external, or production database was read or mutated.

Because the exact reviewed head has Important data-integrity defects, no `data_review` pass receipt should be recorded for this report.
