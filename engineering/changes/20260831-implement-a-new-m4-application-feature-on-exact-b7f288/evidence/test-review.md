# Final independent test re-review — M4 durable factory control plane

## Verdict

**PASS**

- Route: `b7f288f1e81e`
- Base SHA: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Prior reviewed HEAD: `4230dc8e73bcf4dfcf6c60d294d379d44a30c698`
- Reviewed product HEAD: `83e6b0d0c29e813932aa29b0d72ac4d85d27df7b`
- Focused fix range: `4230dc8e73bcf4dfcf6c60d294d379d44a30c698..83e6b0d0c29e813932aa29b0d72ac4d85d27df7b`
- Full reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..83e6b0d0c29e813932aa29b0d72ac4d85d27df7b`
- Exact-head verification fingerprint: `9a9dd64921cc5edf8889330b79732016c0235cc37e4a27c712a05128b3659746`

No Critical or Important test gap remains. TR-003 is closed for both authority forms and both race orderings; the schema-008 upgrade is exercised with non-empty unsafe accounting state; exhausted ordinary-event budgets no longer roll back mandatory release/reconcile/cancel cleanup; and all previously accepted concurrency, fencing, capacity, retry, budget, kill, bounded reconciliation, role, audit, index, bootstrap and UDS evidence remains green.

## Findings

No Critical or Important findings.

### Minor — capacity threshold filling remains sequential

The suite proves a real two-worker race for one task and exact global-reader 20/21, repository-reader 10/11 and writer 1/2 boundaries, but fills the threshold cases sequentially. A barrier-based last-slot race remains useful hardening. It is not a blocker because the database-owned allocation path is exercised under contention elsewhere and each exact capacity rejection is asserted against real PostgreSQL.

### Minor — deadlock orchestration uses timing delays

The cancel/reconcile regression contends both operations behind the same database capacity lock and bounds both futures, but uses short sleeps to arrange waiter order (`factory/tests/test_postgres_integration.py:1172-1201`). A database-side synchronization barrier would make historical lock-reversal detection more deterministic. The current test remains behavior-bearing and the implementation now visibly acquires capacity before task/run locks in both paths.

### Minor — exit container cleanup omits explicit volume removal

The runner always removes its unique disposable container in `finally`, but does not request removal of anonymous volumes. This is local test hygiene only.

## TR-003 authority TOCTOU closure

| Required ordering | Concrete assertion | Result |
| --- | --- | --- |
| Observation revoked before validation | The observation row is revoked first; intake must raise `StoreError`, then the test queries the source and requires task count `0` (`factory/tests/test_postgres_integration.py:235-257`). | PASS |
| Exception revoked before validation | The same test repeats the exact rejection and zero-task assertion for a repository/policy/action-bound bootstrap exception. | PASS |
| Observation revoked after successful validation | A pausing store signals only after the database validator returns. The concurrent revoker cannot complete within 250 ms, intake resumes and commits, then revocation completes; the test asserts blocking, `accepted.created`, commit ordering, and rejection of later intake using the revoked authority (`factory/tests/test_postgres_integration.py:259-316`). | PASS |
| Exception revoked after successful validation | The same two-thread post-validation ordering is repeated for the exception table, including later rejection. | PASS |
| Lock semantics | Forward migration 010 replaces both validators with fixed-search-path `SECURITY DEFINER` functions whose qualifying row reads use `FOR SHARE`, which conflicts with non-key `revoked_at` updates through intake commit (`factory/src/adaptive_factory/resources/010_authority_accounting_and_cleanup.sql:1-36`). | PASS |

These tests are non-vacuous: the post-validation barrier is inside the live intake transaction, the revoker is started only after validation, premature completion is explicitly probed, and commit order is measured after each connection context commits. They directly cover the interleaving missed by the prior revoke-before-validation-only test.

## Schema-008 upgrade and accounting safety

The upgrade regression creates a separate disposable database, applies and records exact migrations 001-008, and seeds a real legacy `retry` task with a failed run, one live full cost/token/wall reservation, nonzero task reservation counters and `accounting_blocked=false` (`factory/tests/test_postgres_integration.py:984-1048`). It then proves:

- only migrations 009 and 010 are applied;
- readiness is `ready`, schema version is 10 and accounting consistency is true after quarantine;
- the legacy task is `needs_human`, retains its live reservation evidence and exact reserved totals, and cannot be claimed;
- owner-side reintroduction of unsafe `retry`/unblocked state makes readiness `not_ready` and still cannot be claimed because the claim query independently excludes live reservations and nonzero counters (`factory/tests/test_postgres_integration.py:1049-1091`).

Migration 010 performs a forward-only quarantine rather than deleting or settling historical evidence (`factory/src/adaptive_factory/resources/010_authority_accounting_and_cleanup.sql:41-70`). Readiness and claim are independently asserted, so the case cannot pass merely because migration metadata reached version 10.

## Exhausted-event mandatory cleanup

The tests deliberately consume an ordinary event budget of two with intake and claim, then exercise every requested cleanup path:

| Path | State/idempotency assertions | Exact cleanup assertions | Result |
| --- | --- | --- | --- |
| Worker release | Release and exact command replay both return `needs_human`; task has no current run and three total events, with the third marked mandatory (`factory/tests/test_postgres_integration.py:853-879`). | One mandatory `released` event, one release audit fact, zero live allocation, global reader count `0`, repository reader count `0`. | PASS |
| Expired-run reconcile | First reconcile repairs exactly one; replay/second pass repairs zero (`factory/tests/test_postgres_integration.py:918-936`). | One mandatory release event, one audit fact and exact zero allocation/counters through the shared assertion helper (`:122-136`). | PASS |
| Operator cancel | First cancel and exact-key replay both return `cancelled` (`factory/tests/test_postgres_integration.py:938-955`). | One mandatory cancelled event, one cancel audit fact and exact zero allocation/counters. | PASS |

Production counting separates ordinary budgeted events from idempotent mandatory cleanup facts, while sequence numbers remain monotonic (`factory/src/adaptive_factory/store.py:191-231`). An exhausted retry is routed to `needs_human` before cleanup rather than placed into an immediately unclaimable retry loop; release, orphan reconcile, supersession and cancel all use the explicit mandatory path.

## All prior acceptance coverage retained

| Area | Direct evidence | Result |
| --- | --- | --- |
| Immutable intake/idempotency | Closed contracts reject unknown versions/fields, invalid identity, stale authority and handoff mismatches. Complete frozen intent changes alter digest/key; exact replay deduplicates while changed source, limit or authority supersedes without rewriting accepted intent. | PASS |
| Claims, fencing and capacity | Two workers compete for one task and exactly one wins; reclaim issues a higher fence; late and hidden-allocation mutations fail. Exact 20 global readers, 10/repository and one writer boundaries remain asserted. | PASS |
| Retry/dead/budgets | Only the closed infrastructure set retries and attempt three becomes dead. Cost/token/wall reservations, usage/output limits, event limit, repair cap, database deadline, missing accounting and cross-attempt reservations all have direct fail-closed PostgreSQL cases. | PASS |
| Kill/reconcile | Global and repository kills block only their scopes. Reconciliation proves orphan isolation, repair replay, counter fail-closed behavior, 100+1 keyset paging and the effective transaction setting `statement_timeout='5s'`. | PASS |
| Authorization/idempotent commands | Bearer, scope, repository, worker ownership, wildcard global operations, exact result replay, changed-command conflict, empty-claim replay and durable correlation are directly asserted. Malformed closed commands return bounded 4xx responses. | PASS |
| Effective roles/audit | Forbidden intent/event/audit/capacity/allocation DML is executed under `factory_runtime` and must raise `InsufficientPrivilege`; supported lifecycle still works. Audit-v2 tampering of task, run or correlation identity invalidates verification. | PASS |
| Query plans | Populated-data `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` assertions require the named claim, audit, usage, active-reservation and reconcile indexes. | PASS |
| Local bootstrap/UDS | The shipped admin path creates and validates an effective runtime login. Uvicorn serves an actual Unix listener; HTTPX-over-UDS proves unauthenticated `401` and authenticated actor response. Absolute/no-follow credential ancestry is negative-tested. | PASS |
| Restart | The runner performs an actual container restart, reconnects with a fresh store, repairs once, replays with zero repairs, issues a higher fence and rejects the late holder. | PASS |

## Verification evidence

The inspected receipt was created at `2026-09-01T21:10:24Z` for exact HEAD `83e6b0d0c29e813932aa29b0d72ac4d85d27df7b` and fingerprint `9a9dd64921cc5edf8889330b79732016c0235cc37e4a27c712a05128b3659746`:

```text
14/14 verifier checks: PASS
python-unittest: 488 tests in 508.509s — OK
factory-unit: 24 tests in 0.011s — OK
factory-postgres-exit: 63 tests in 33.432s — OK
restart: one repair; replay no-op; higher fence; late holder rejected — PASS
source-stability: PASS
```

The durable implementation evidence additionally records the residual focused PostgreSQL set at 5/5 in 4.049s, the strengthened schema-008 upgrade case at 1/1 in 1.031s, migration tests 4/4, installer tests 17/17 and the fresh 63/63 exit plus restart. `git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..83e6b0d0c29e813932aa29b0d72ac4d85d27df7b` produced no output during this review.

This review changed only this report. It did not modify product code, receipts, Git, databases, external systems, production or Trust CI state. As usual, writing a review report changes the repository fingerprint; the coordinator must record all final route reviews and verification against the resulting single evidence tree before AC-014/local closure.
