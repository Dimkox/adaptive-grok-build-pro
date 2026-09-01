# Test review — M4 durable factory control plane

## Verdict

**FAIL**

Route: `b7f288f1e81e`  
Base SHA: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`  
Reviewed head SHA: `01643c6594947535e690c5722f710081c9b9db9f`  
Reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..01643c6594947535e690c5722f710081c9b9db9f`  
Worktree at review start: clean; `HEAD` matched the reviewed head exactly.

The checked-in suite passes, including 30/30 tests on a fresh disposable PostgreSQL 17 instance, but Important behavioral and evidence gaps remain. Under the review rubric, any Important gap is a failing review.

## Findings

### Important — leased-task supersession leaks capacity and breaks reconciliation

`factory/src/adaptive_factory/store.py:157-179` supersedes every eligible nonterminal task by clearing `current_run_id`/`current_fence`, but it does not release the live run, allocation, or capacity counters. Later, reconciliation selects the still-unreleased expired run at `factory/src/adaptive_factory/store.py:658-677`; `_lock_grant` rejects it because the task is no longer `leased` and no longer points at that run (`factory/src/adaptive_factory/store.py:424-439`). The transaction therefore fails instead of recovering the leaked allocation.

The PostgreSQL supersession test only supersedes a queued task (`factory/tests/test_postgres_integration.py:54-65`). It never claims the task first and therefore gives a false positive for AC-002, AC-005, AC-009, and the stated evidence-preserving supersession failure case.

Targeted reproduction on the fresh review database produced:

```text
old_task ('superseded', None, None)
old_run ('leased', None)
global_reader_count 1
allocation_released_at None
reconcile_error FenceError stale or expired fence
```

Required coverage: supersede an actively leased reader and writer; assert the old run/allocation is closed, global/repository counters are decremented exactly once, the stale grant is rejected, and repeated reconciliation succeeds without leaking or double-decrementing capacity.

### Important — mutation idempotency is asserted at the header but not implemented or tested

The API validates an `Idempotency-Key` for claim, heartbeat, proposal/release, and reconciliation, then discards it (`factory/src/adaptive_factory/api.py:184-205`, `factory/src/adaptive_factory/api.py:207-237`, `factory/src/adaptive_factory/api.py:261-279`). The service/store mutation interfaces receive no command key (`factory/src/adaptive_factory/service.py:49-70`, `factory/src/adaptive_factory/service.py:112-116`). A replay can therefore mutate twice or fail based on the new state rather than return the original command result, contrary to AC-010, the failure-case requirement, and `INV-003` in `change-spec.yaml:19`.

The only API idempotency test checks missing headers on intake (`factory/tests/test_api.py:70-77`); the CLI test merely searches help text (`factory/tests/test_api.py:115-132`). A targeted replay of the same `/v1/proposals` request with the same key produced:

```text
first 200 {'status': 'ready_for_human'}
duplicate 409 {'error': 'conflict', 'code': 'stale_fence'}
```

Required coverage: replay each mutation with the same key and payload and assert the same persisted/result identity; reuse a key with a different payload and assert a closed conflict; include concurrent duplicate submissions.

### Important — the restart and reconciliation evidence does not exercise a PostgreSQL restart or repeated repair

The P1 plan requires “repeated restart reconciliation repairs exactly once” (`test-plan.md:11`) and AC-009/AC-012 require restart-safe, idempotent reconciliation and real restart proof (`requirements.md:13`, `requirements.md:16`). The probe only starts and joins a worker process, manually backdates the lease, and calls reconciliation once (`factory/tests/postgres_restart_probe.py:100-125`). It never stops/restarts PostgreSQL, reconnects after a database restart, or invokes reconciliation a second time. Its PASS message therefore overstates what it proves.

The integration suite also calls reconciliation only once per expired lease (`factory/tests/test_postgres_integration.py:87-103`) and does not assert ordered keyset pagination, the 100-candidate boundary, replay after partial progress, or the five-second timeout failure path.

Required coverage: restart the disposable PostgreSQL service/container after a committed claim, reconnect with a fresh store/service, run reconciliation twice (and concurrently), assert exactly one repair/higher fence, assert stable ordered cursor paging at 100/101 candidates, and exercise timeout/rollback behavior.

### Important — the exact-tree verification receipt omits the P0 API and PostgreSQL suites

The verifier selects only contract, state, migration, and service modules (`.grok-stack/adaptive_grok/verification.py:574-587`). It excludes `test_api.py`, `test_postgres_integration.py`, and `postgres_restart_probe.py`. The exact-head verification receipt consequently records only 19 dependency-free factory tests, while the high-risk P0/P1 evidence is prose/manual evidence outside the fingerprint-bound verification run. This does not satisfy AC-014’s one-final-fingerprint condition (`requirements.md:18`) or the test plan’s real-PostgreSQL exit intent.

This review independently ran all 30 tests on the exact head and they passed, but those tests still contain the gaps above and this manual run is not the route verification receipt. Required gate coverage: make an explicit disposable PostgreSQL integration/restart profile mandatory for this high-risk route, fail rather than skip when the required disposable URL/project is absent, and bind its command output to the same final tree fingerprint.

## Additional coverage risks

- The advertised 20/10/1 capacity test fills readers and writers sequentially (`factory/tests/test_postgres_integration.py:105-133`). Only the one-task claim test uses two threads. Add competing transactions at the 20th/21st global reader, 10th/11th repository reader, and first/second writer boundaries.
- The database role test checks privilege metadata while the suite/store connection remains the database owner (`factory/tests/test_postgres_integration.py:266-287`). Execute representative runtime and audit operations under `SET ROLE factory_runtime` / `factory_audit_reader`, including expected denied statements.
- The integration retry path covers only `worker_lost` through attempt three (`factory/tests/test_postgres_integration.py:135-147`). Persistently exercise every retryable class plus at least one nonretryable class and verify run, attempt, task, event, audit, and capacity state after each failure.

## Commands and evidence

```text
git rev-parse HEAD
  01643c6594947535e690c5722f710081c9b9db9f

git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..01643c6594947535e690c5722f710081c9b9db9f
  PASS (no output)

PYTHONPATH=factory/src:. python3 -m unittest discover -s factory/tests -v
  FAIL: 1 import error (FastAPI dependency absent), 5 PostgreSQL tests skipped

FACTORY_TEST_DATABASE_URL=<fresh-disposable-postgresql-17> PYTHONPATH=factory/src:. <isolated-venv>/bin/python -m unittest discover -s factory/tests -v
  PASS: Ran 30 tests in 6.476s, OK

FACTORY_TEST_DATABASE_URL=<same-disposable-db> ... factory/tests/postgres_restart_probe.py
  PASS message emitted, but no PostgreSQL restart occurred

targeted leased-supersession probe
  FAIL: leaked reader capacity/allocation; reconciliation raised FenceError

targeted duplicate-proposal probe
  FAIL: first request 200; same-key replay 409 stale_fence
```

The uniquely named disposable review container `m4-test-review-b7f288-01643c6` and its anonymous volume were removed after testing; that test data is not recoverable. No shared, Trust CI, external, or production database was used.
