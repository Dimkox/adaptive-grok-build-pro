# Test review round 2 — M4 durable factory control plane

## Verdict

**FAIL**

- Route: `b7f288f1e81e`
- Base SHA: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Reviewed head SHA: `9bc51e81dddb8fc02f22171b586eb8c9caa7f304`
- Reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..9bc51e81dddb8fc02f22171b586eb8c9caa7f304`
- Exact-head verification fingerprint: `bae655f75a7cdb67f3ef7dced1c4f51cd83c2f016b558dbb44384a613335fcf2`

The requested spelling `9bc51e8c` is not a Git object. The unambiguous requested prefix `9bc51e8` and clean worktree `HEAD` both resolve to the full SHA above, which is the tree reviewed.

The prior leased-supersession, actual-restart, and verifier-coverage blockers are repaired and pass. Positive command replay also passes, but claim idempotency still changes a previously returned no-work result into a lease. That Important contract defect requires a failing review.

## Findings

### Important — no-work claim results are not idempotent and can later lease a task

`PostgresFactoryStore.claim()` checks for a prior command at `factory/src/adaptive_factory/store.py:406-414`, but every no-grant path returns without recording the result: kill switch at `factory/src/adaptive_factory/store.py:415-416`, global capacity at `factory/src/adaptive_factory/store.py:434-435`, repository capacity at `factory/src/adaptive_factory/store.py:443-444` and `factory/src/adaptive_factory/store.py:457-458`, empty queue at `factory/src/adaptive_factory/store.py:452-454`, and exhausted attempts at `factory/src/adaptive_factory/store.py:464-471`. Only a successful lease reaches `_record_command` at `factory/src/adaptive_factory/store.py:515-523`.

Consequently, retrying the exact same API command after the queue changes does not replay the original `{"grant": null}` result; it performs a new claim and leases work. This violates AC-010 and `INV-003`, and it is precisely the lost-response/retry case durable idempotency is intended to control.

The new test covers only a successful claim replay while a task is already queued (`factory/tests/test_postgres_integration.py:211-230`). It is therefore a false-positive for the complete mutation-idempotency contract.

Targeted fresh-PostgreSQL reproduction:

```text
first 200 {'grant': None}
same_key_replay_after_task_arrives 200 {'grant': {'task_id': '...', 'run_id': '...', ...}}
command_results 1
```

Required repair and coverage: persist `{"grant": null}` before every no-grant return; replay it after task arrival, kill removal, and capacity release; reject changed request payloads under the same key; and test concurrent same-key empty and successful claims.

## Prior Important issue retest

| Prior blocker | Round-2 evidence | Result |
| --- | --- | --- |
| Leased supersede/cancel leaked run, allocation, and capacity; reconciliation failed | `test_cancel_and_supersede_release_leases_capacity_once` passed for reader cancel and writer supersede; direct code inspection confirms `_close_active_lease` closes run/allocation/attempt and decrements locked counters (`factory/src/adaptive_factory/store.py:540-575`). | PASS |
| Positive API proposal/claim replay returned state-dependent conflict | `test_api_mutations_replay_exact_results_and_reject_changed_commands` passed exact successful claim/proposal/kill replay and changed-payload conflicts. The no-work claim finding above remains. | PARTIAL / FAIL |
| Restart probe did not restart PostgreSQL or reconcile twice | `postgres_restart_probe.py` invokes `docker restart`, reconnects with a fresh service, reconciles twice, asserts repairs `1` then `0`, obtains a higher fence, and rejects the late heartbeat (`factory/tests/postgres_restart_probe.py:68-96`). It passed independently and inside the verifier exit run. | PASS |
| Exact-tree verifier omitted API/PostgreSQL/restart tests | PR/release verification now invokes `factory/tests/run_disposable_exit.py` (`.grok-stack/adaptive_grok/verification.py:589-597`). Exact-head receipt `created_at=2026-09-01T09:09:15+00:00` records `factory-unit` PASS and `factory-postgres-exit` PASS with 40 tests plus actual restart. | PASS |

## Test-honesty observations

### Minor — advertised capacity limits are still filled sequentially

The 20-reader, 10-per-repository, and one-writer boundary test still claims sequentially (`factory/tests/test_postgres_integration.py:333-371`). The separate two-thread test proves contention for one task, not simultaneous transactions at each capacity boundary. Add barriers and competing transactions at reader 20/21, repository reader 10/11, and writer 1/2 so the P0 “competing claims, 20/10/1 capacity” plan is exercised literally.

### Minor — the disposable exit runner leaves its anonymous PostgreSQL volume behind

The runner removes the container with `docker rm -f` but omits `-v` (`factory/tests/run_disposable_exit.py:55-56`). Since the PostgreSQL image uses a data volume, the container is gone but its anonymous test-data volume can remain recoverable/orphaned. Cleanup should remove the exact container with its volume and verify both are absent.

### Minor — exact-range whitespace is not covered by the receipt's clean-worktree diff check

`git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..9bc51e81dddb8fc02f22171b586eb8c9caa7f304` reports committed trailing whitespace in round-1 evidence files, while the receipt's `git diff --check` on a clean worktree passes. This does not affect product behavior, but the check name overstates exact-range coverage.

## Commands and results

```text
git rev-parse HEAD
  9bc51e81dddb8fc02f22171b586eb8c9caa7f304

python3 factory/tests/run_disposable_exit.py
  PASS: 40 tests in 14.553s
  PASS: PostgreSQL restarted; one repair; replay no-op; higher fence; late holder rejected
  PASS: disposable PostgreSQL + API + effective roles + actual restart/reconciliation

python3 -m unittest tests.test_verification_doctor.VerificationTests.test_python_pr_requires_factory_postgres_api_and_restart_exit_runner -v
  PASS: 1 test in 2.145s

exact-head verification receipt inspection
  PASS: head 9bc51e81dddb8fc02f22171b586eb8c9caa7f304
  PASS: factory-unit exit=0
  PASS: factory-postgres-exit exit=0

targeted same-key empty-claim replay on fresh PostgreSQL 17
  FAIL: first response grant=null; replay after task arrival returned a live grant

targeted concurrent reconciliation with two command keys and a forced shared lock wait
  PASS: both calls completed; candidates=(1,1), repairs=(0,1), final global reader count=0, live allocations=0

git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..9bc51e81dddb8fc02f22171b586eb8c9caa7f304
  Minor evidence hygiene failure: committed trailing whitespace in round-1 review reports
```

The explicitly named manual review container `m4-test-review-r2-9bc51e8` and its anonymous volume were removed after testing. The exit runner removed its own container. No shared, Trust CI, external, or production database was read or mutated.
