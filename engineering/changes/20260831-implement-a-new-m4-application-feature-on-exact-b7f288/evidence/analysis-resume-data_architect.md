# M4 resumed data/concurrency analysis

## Binding and status

- Route: `b7f288f1e81e`
- Change: `20260831-implement-a-new-m4-application-feature-on-exact-b7f288`
- Accepted base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Inspected committed HEAD: `9727bc30c82bb44a86db0ef5b62e507b5527207a`
- Inspected Git tree: `5feb9a74eda6c54cd37539a2c5dda378a5e27853`
- Role: route-selected read-only `data_architect`

**Status: BLOCKED for acceptance pending two Important data repairs and fresh exact-tree PostgreSQL evidence.** No Critical finding was identified. This analysis was static/read-only apart from this report; it did not run or mutate a database or external system. `git diff --check 67714a1..9727bc3 -- factory <change-package>` produced no output.

## Important findings

### DATA-RESUME-001 — a live lease that crosses the task deadline cannot be reconciled

`reconcile()` deliberately selects every unreleased allocation whose run lease is expired, without excluding a task whose hard deadline is also expired (`factory/src/adaptive_factory/store.py:1177-1183`). It then calls `_release_locked(..., allow_expired=True)` for the current fenced run (`store.py:1194-1205`). The supposed reconciliation exception only bypasses the run lease-expiry predicate: `_lock_grant()` still unconditionally requires `t.deadline_at > clock_timestamp()` (`store.py:813-829`, especially lines 822-824). Therefore a valid current lease left behind until after the four-hour deadline raises `FenceError` inside reconciliation. The whole reconciliation transaction rolls back, so its capacity allocation remains live and the same candidate can abort every later pass; earlier repairs in that batch roll back as well.

This is not an artificial ordering: claim caps `lease_expires_at` at the task deadline (`store.py:679-685`), so a restart/outage that lasts through the deadline naturally creates the state. It conflicts with RQ-007's hard wall-budget behavior, RQ-009's restart-safe/idempotent bounded reconciliation, and RQ-012's real restart/reconciliation requirement. It also leaves global/repository capacity occupied indefinitely unless an operator separately cancels the task.

The PostgreSQL suite does not cover this intersection. The deadline test only proves that a worker heartbeat is fenced after changing the task deadline to the past (`factory/tests/test_postgres_integration.py:1440-1455`). Reconciliation and restart cases expire only `runs.lease_expires_at` while the task deadline stays in the future (`test_postgres_integration.py:1428-1435`, `1467-1475`; `factory/tests/postgres_restart_probe.py:82-107`).

Required repair: add a capacity-first control-plane cleanup path that validates the current task/run/fence but is explicitly permitted to close a lease after both lease and task deadline expiry. It must release run/allocation exactly once, clear the task's current run/fence, emit one mandatory cleanup event and hash-chained audit fact, and choose a non-claimable deadline terminal state (`dead` or `needs_human`) according to an explicit policy; it must not return the task to `retry`. A single poisoned row must not roll back other bounded candidates. Also decide whether queued/retry tasks whose deadline expires without a live run must be terminalized by the same bounded reconciler; today claim merely skips them (`store.py:621-627`) and they remain counted as queued/retry forever.

### DATA-RESUME-002 — cancel/supersede can strand unresolved accounting and make readiness permanently inconsistent

Budget reservation creates a live `budget_reservations` row and increments the task's cost/token/wall reserved aggregates (`factory/src/adaptive_factory/store.py:943-1007`). Cancel and changed-intent supersession both use `_terminalize_task()`, whose lease cleanup closes only run, attempt, capacity allocation, and current run/fence (`store.py:732-784`); it neither settles the reservation nor marks unresolved accounting as blocked.

If a reservation committed before terminalization, no supported worker path can settle it afterward because `_lock_grant()` requires the task and run to remain the current live leased pair (`store.py:813-829`). The effects differ but are both unsafe:

- a superseded task remains `accounting_blocked=false` with a live reservation/nonzero aggregates, which `_accounting_consistent()` explicitly classifies as inconsistent (`store.py:167-182`); `/health/ready` can remain `not_ready` after an otherwise valid changed-intent intake;
- a cancelled task is omitted from that readiness predicate, so readiness can report ready while fixed metrics retain permanently active reserved cost/token/wall and no supported settlement path exists.

The schema-008 recovery migrations already establish the safe pattern: preserve unresolved evidence and mark unsafe terminal history `accounting_blocked=true`, with `superseded/accounting_blocked` accepted as an explicit quarantine (`factory/src/adaptive_factory/resources/010_authority_accounting_and_cleanup.sql:41-70`; `011_legacy_accounting_quarantine.sql:1-27`). Runtime terminalization does not apply that rule. The current cancel/supersede tests claim and terminalize without first reserving budget and assert only run/allocation/counter cleanup (`factory/tests/test_postgres_integration.py:411-448`); the prior-attempt accounting test exercises worker failure, not cancel/supersede (`test_postgres_integration.py:1496-1521`).

Required repair: in the same terminalization transaction, detect any active reservation, nonzero reserved aggregate, or already-blocked accounting and apply the approved evidence-preserving accounting quarantine. Do not silently release a reservation unless policy can prove no provider work occurred. Record the quarantine in the mandatory event/audit metadata without sensitive payloads. Add real PostgreSQL cases for both cancel and supersede after reservation, including exact replay, no live capacity, retained evidence, `accounting_blocked=true`, coherent fixed metrics, and ready/not-ready behavior consistent with the chosen recovery contract.

## Reviewed areas without a new acceptance defect

- Migration discovery/application is contiguous `001..013`, checksum-bound and atomic under one advisory-locked transaction with five-second lock/statement limits (`factory/src/adaptive_factory/migrations.py:40-71`, `146-189`). Migration `013` adds a closed `0..2` persisted projection, backfills typed frozen values, and intentionally maps untyped legacy history to the former limit `2` (`resources/013_persisted_infrastructure_retry_limit.sql:1-18`). Intake persists the accepted value directly (`store.py:464-483`).
- Release and reconciliation use the persisted limit in `classify_retry`; the initial attempt plus exactly the accepted number of retries is implemented correctly (`factory/src/adaptive_factory/state.py:126-150`; `store.py:860-869`). Claim detects an already exhausted schema-012 retry row before allocating a new fence/run/attempt and adds mandatory event plus audit (`store.py:621-672`, fence allocation begins at line 673). The real-PG source exercises accepted limits `0/1/2` on release/reconciliation and schema-012 upgrade exhaustion for `0/1` (`factory/tests/test_postgres_integration.py:952-1075`, `1523-1711`), while the restart probe checks persisted `0` versus `2` behavior after an actual database restart (`postgres_restart_probe.py:66-127`).
- Migration `012` builds a one-row authoritative metrics snapshot under write-conflicting source locks, installs same-transaction delta triggers, revokes runtime table DML/read, and grants only fixed snapshot plus saturating no-argument fence-rejection capabilities (`resources/012_bounded_metrics_snapshot.sql:1-273`). `metrics()` performs one fixed-row read with five-second statement and 500-millisecond lock limits; best-effort fence observation is separately bounded (`store.py:198-238`). The source tests cover effective-role denial, concurrent monotonic saturation, coherent lease/capacity snapshot, lock timeout, and non-masking stale-fence behavior (`test_postgres_integration.py:1178-1390`). No new snapshot/fencing defect was found in this pass.
- Capacity allocation/release stays behind SECURITY DEFINER functions that lock canonical counter keys before mutation (`resources/007_capacity_authority.sql:11-169`), and supported release/cancel/reconcile paths use capacity-before-task/run ordering. The current deadline finding is an authorization predicate error after those locks, not a counter-underflow or fence-monotonicity error.

## Missing migration/recovery evidence and focused verification

The current receipts are not evidence for HEAD `9727bc3`: `python3 scripts/grok_status.py` reports verification and all five reviews stale after repository/spec/architecture/governance changes, and the retained data review is bound to product `4f75558` / evidence head `9fe779a`, before migration `013` and the later store changes. RQ-014 remains unchecked. Existing recorded 70/70 PostgreSQL evidence likewise predates the current repair wave.

Before a PASS claim, run on a newly created disposable PostgreSQL 17 database/container only:

1. RED/GREEN deadline case: claim and reserve as applicable, move both run lease and task deadline into the past, reconcile twice, and assert first-pass one repair, second-pass zero, non-claimable task state, one mandatory event/audit fact, zero live allocation/counter, coherent metrics, and stale worker rejection. Include another expired candidate after the poisoned row to prove one row cannot roll back/starve the page.
2. RED/GREEN accounting terminalization matrix: reader/writer x cancel/supersede after zero and positive reservations. Assert exact command replay, no capacity leak, retained immutable reservation evidence with explicit accounting quarantine, readiness consistency, audit-chain validity, and fixed snapshot agreement.
3. Migration `012 -> 013` cutover: typed limits `0/1/2`, documented untyped legacy fallback, exhausted retry handling, empty replay, checksum mismatch denial, and an induced lock/statement timeout proving schema/registry rollback is atomic. Record pre-cutover row counts and the bounded migration duration; the single UPDATE backfill and migration-012 task trigger make this volume-specific evidence necessary before any persistent local rollout.
4. Re-run the complete disposable exit harness and actual restart probe, then root `python3 scripts/grok_verify.py --mode pr` and all route-selected reviews/receipts against one unchanged committed fingerprint. A separately authorized rollout still needs the documented backup restored into a distinct comparison database plus exact-schema-013 readiness/capacity/accounting/audit/two-pass-reconcile evidence; no such persistent migration or restore was performed in this analysis.

## Conclusion

Schema `013` retry-limit persistence, the migration-012 fixed metrics snapshot, supported fence checks, and ordinary future-deadline retry/reconciliation paths are coherent in the inspected source. M4 should not receive a data-analysis PASS, however, until deadline-crossing reconciliation and terminalization with unresolved accounting are repaired and proven on real disposable PostgreSQL, followed by fresh fingerprint-bound verification and independent reviews.
