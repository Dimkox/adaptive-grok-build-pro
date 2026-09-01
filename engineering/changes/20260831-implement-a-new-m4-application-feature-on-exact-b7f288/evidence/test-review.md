# Test review round 3 — M4 durable factory control plane

## Verdict

**PASS**

- Route: `b7f288f1e81e`
- Base SHA: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Reviewed head SHA: `8435e23458885a48e2d5784f8cd01e84d978c28c`
- Reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..8435e23458885a48e2d5784f8cd01e84d978c28c`
- Exact-head verification fingerprint: `7f5f5a2c7eb5985b7b83643fee8158aba5a5fc4693eba826f58d9e9e1d519f70`

No Critical or Important test, behavioral-contract, PostgreSQL concurrency/restart, failure-path, effective-role, or verifier-inclusion gap remains in the reviewed tree. The prior blockers reproduce as fixed on fresh disposable PostgreSQL 17.

## Findings

No Critical or Important findings.

### Minor — capacity boundary evidence remains sequential

The suite proves one-task claim contention with two threads (`factory/tests/test_postgres_integration.py:369-405`) and proves exact 20-global-reader, 10-repository-reader, and one-writer ceilings (`factory/tests/test_postgres_integration.py:428-465`), but it fills the three capacity boundaries sequentially. A future hardening test should use barriers for simultaneous transactions at reader 20/21, repository reader 10/11, and writer 1/2. This is not a release blocker because the transactional counter lock is exercised by the contention test and direct boundary assertions pass against the real database.

### Minor — no full HTTP-over-UDS round trip is automated

The server test proves the listener is an owned `AF_UNIX` socket at mode `0660` and refuses unsafe paths (`factory/tests/test_server.py:13-33`); API/auth behavior is exercised in-process, and the CLI uses `httpx.HTTPTransport(uds=...)`. The suite does not start Uvicorn and send one authenticated CLI/API request through the actual socket. Add that end-to-end smoke test when the local service is packaged for rollout.

### Minor — the exit runner should remove its anonymous volume explicitly

`factory/tests/run_disposable_exit.py:55-56` removes its uniquely named container with `docker rm -f` but omits `-v`. The test remains isolated and no container survives a successful run, but explicit volume removal would avoid orphaned disposable PostgreSQL data.

## Prior blocker disposition

| Prior blocker | Round-3 evidence | Result |
| --- | --- | --- |
| Leased cancel/supersede leaked runs, allocations, and capacity; reconciliation then failed | `test_cancel_and_supersede_release_leases_capacity_once` passed for reader cancel and writer supersede; `test_reconcile_isolates_orphan_and_repairs_valid_expired_lease` passed and replay repaired zero. | PASS |
| Successful proposal/claim replay was state-dependent | Successful claim, proposal, kill, reserve-budget, and usage replays return the persisted result; changed commands return conflict (`factory/tests/test_postgres_integration.py:211-273`, `factory/tests/test_postgres_integration.py:300-367`). | PASS |
| Empty claim replay later leased newly arrived work | Every no-grant path now records `{"grant": null}` (`factory/src/adaptive_factory/store.py:413-477`); `test_empty_claim_is_replayed_after_work_arrives` passed and verified stored correlation/result (`factory/tests/test_postgres_integration.py:275-298`). | PASS |
| Concurrent same-key commands could race | `_command_replay` serializes each command key using an advisory transaction lock (`factory/src/adaptive_factory/store.py:89-102`). A targeted two-thread same-key API claim returned byte-equivalent grants with exactly one run and one command record. | PASS |
| Restart probe did not restart PostgreSQL or reconcile twice | The probe executes `docker restart`, reconnects through a fresh store/service, reconciles twice with repairs `1` then `0`, issues a higher fence, and rejects the stale holder (`factory/tests/postgres_restart_probe.py:68-96`). | PASS |
| PostgreSQL/API/restart evidence was outside exact-tree verification | PR/release verification invokes the mandatory exit runner (`.grok-stack/adaptive_grok/verification.py:589-597`). The exact-head receipt records `factory-unit`, `factory-postgres-exit`, `source-stability`, and overall verification as PASS. | PASS |
| Runtime role could mutate policy/identity columns | Migration 006 revokes table UPDATE, then grants only `capacity_counters.active_count` (`factory/src/adaptive_factory/resources/006_runtime_policy_privileges.sql:1-2`). Integration tests execute allowed/denied statements under `SET ROLE factory_runtime` (`factory/tests/test_postgres_integration.py:608-652`). | PASS |

## Test honesty and failure paths

- The disposable exit runner fails closed because PR/release verification invokes it unconditionally when present; absence of Docker, `uv`, dependencies, PostgreSQL readiness, a test pass, or the restart probe causes a nonzero check.
- The real suite uses effective `factory_runtime` connections, validates schema version 6 readiness, denies audit/intent/event/identity/capacity-ceiling mutation, and permits only the active counter update needed by runtime behavior.
- Idempotency tests check exact replay, changed-payload conflict, correlation persistence, replay before stale-fence validation, empty results, and concurrent same-key serialization.
- PostgreSQL tests cover queued supersession, leased cancel/supersession, orphan reconciliation, sequential replay, claim contention, capacity ceilings, fencing, retry-to-dead, accounting limits and missing accounting, kill switches, audit verification, and role isolation.
- The restart evidence is honest: it restarts the actual disposable database container rather than merely ending a worker process.

## Commands and results

```text
git rev-parse HEAD
  8435e23458885a48e2d5784f8cd01e84d978c28c

git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..8435e23458885a48e2d5784f8cd01e84d978c28c
  PASS (no output)

python3 factory/tests/run_disposable_exit.py
  PASS: 42 tests in 15.371s
  PASS: PostgreSQL restarted; one repair; replay no-op; higher fence; late holder rejected
  PASS: disposable PostgreSQL + API + effective roles + actual restart/reconciliation

exact-head verification receipt inspection
  PASS: status=pass
  PASS: head=8435e23458885a48e2d5784f8cd01e84d978c28c
  PASS: git-diff-check exit=0
  PASS: factory-unit exit=0
  PASS: factory-postgres-exit exit=0
  PASS: source-stability repository fingerprint remained stable

targeted concurrent same-key claim on fresh PostgreSQL 17
  PASS: two HTTP responses were identical
  PASS: runs=1; claim command records=1
  PASS: store role transition observed factory_test -> factory_runtime
```

The explicitly named manual review container `m4-test-review-r3-8435e23` and its anonymous volume were removed after testing. The mandatory exit runner removed its own container. No shared, Trust CI, external, or production database was read or mutated.
