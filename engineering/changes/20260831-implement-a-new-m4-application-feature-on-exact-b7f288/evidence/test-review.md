# Test review round 5 — M4 durable factory control plane

## Verdict

**PASS**

- Route: `b7f288f1e81e`
- Base SHA: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Reviewed head SHA: `f82134de35e531a8b3bbf235ad480254ba40f1fe`
- Reviewed full range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..f82134de35e531a8b3bbf235ad480254ba40f1fe`
- Reviewed round-five delta: `9fd2a56c57f834ad39c03a2f748bdbaefc79c91c..f82134de35e531a8b3bbf235ad480254ba40f1fe`
- Exact-head verification fingerprint: `e4ac983f20ea22120e98b5eb6597fa6d47486225000a29caf1ab45cadc726b6a`

No Critical or Important test, contract, PostgreSQL restart/reconciliation, effective-role, failure-path, installer, or verifier-inclusion gap remains. Runtime allocation release/unrelease DML is denied, a hidden allocation invalidates all tested worker mutations and makes reconciliation fail closed, and ordinary lifecycle plus actual restart/reconcile continue to pass on fresh PostgreSQL 17 from both source and a clean materialized install.

## Findings

No Critical or Important findings.

### Minor — capacity threshold filling remains sequential

The suite proves a concurrent one-task/two-worker claim race and exact global reader 20/21, repository reader 10/11, and writer 1/2 boundaries, but fills the threshold cases sequentially (`factory/tests/test_postgres_integration.py:369`, `factory/tests/test_postgres_integration.py:428`). A barrier-based last-slot race remains useful hardening. This is not a release blocker because the database-owned locking path is exercised concurrently elsewhere and both fresh-database runs passed each exact threshold assertion.

### Minor — no full HTTP-over-UDS round trip is automated

Socket ownership/mode and API/auth behavior are tested separately, but the suite does not start Uvicorn and send an authenticated request through the actual Unix socket. This is rollout hardening, not a blocker for the requested database-authority delta.

### Minor — the exit runner does not explicitly remove its anonymous volume

`factory/tests/run_disposable_exit.py:55` removes its unique container but omits Docker's volume-removal option. Both review runs removed their containers successfully; explicit anonymous-volume cleanup would avoid local test-volume accumulation.

## Round-five blocker disposition

| Required evidence | Concrete observation | Result |
| --- | --- | --- |
| Runtime cannot release an allocation directly | Migration 008 revokes `UPDATE` on `factory.capacity_allocations` from `factory_runtime` (`factory/src/adaptive_factory/resources/008_allocation_release_authority.sql:1`). The integration test asserts `released_at` update privilege is false and executes an update-to-timestamp under `SET LOCAL ROLE factory_runtime`, expecting `InsufficientPrivilege` (`factory/tests/test_postgres_integration.py:637-658`). | PASS |
| Runtime cannot resurrect an allocation directly | The same effective-role test executes `UPDATE ... SET released_at=NULL` under the runtime role and requires `InsufficientPrivilege` (`factory/tests/test_postgres_integration.py:649-658`). | PASS |
| Hidden allocation invalidates heartbeat | A database-owner fixture hides the grant allocation, then `service.heartbeat` must raise `FenceError` (`factory/tests/test_postgres_integration.py:672-686`). `_lock_grant` requires `a.released_at IS NULL` (`factory/src/adaptive_factory/store.py:581-598`). | PASS |
| Hidden allocation invalidates release | The same corrupted grant's `service.release` raises `FenceError` before task/run/counter mutation (`factory/tests/test_postgres_integration.py:687-688`; `factory/src/adaptive_factory/store.py:618-628`). | PASS |
| Hidden allocation invalidates accounting | Both budget reservation and usage observation raise `FenceError` for the hidden allocation (`factory/tests/test_postgres_integration.py:689-698`). Both production paths validate through `_lock_grant`. | PASS |
| Reconciliation fails closed | Hidden allocation makes readiness `not_ready`, and reconciliation raises the exact counter/allocation inconsistency `StoreError` before processing candidates (`factory/tests/test_postgres_integration.py:699-701`; `factory/src/adaptive_factory/store.py:914-924`). | PASS |
| Normal lifecycle survives least privilege | The effective-runtime test claims, observes usage, releases through the security-definer capacity function, and ends `ready` (`factory/tests/test_postgres_integration.py:659-670`). The corruption test then restores owner state, records usage, completes release to `ready_for_human`, and returns readiness to `ready` (`factory/tests/test_postgres_integration.py:703-716`). | PASS |
| Actual PostgreSQL restart/reconcile/fencing | The probe executes `docker restart`, reconnects through a fresh store/service, reconciles with repairs `1` then `0`, claims a higher fence, and rejects the stale heartbeat (`factory/tests/postgres_restart_probe.py:68-97`). It passed in the source run, installed-copy run, and exact-head root receipt. | PASS |
| Root verifier inclusion | PR/release verification invokes `factory/tests/run_disposable_exit.py` as `factory-postgres-exit` (`.grok-stack/adaptive_grok/verification.py:589-597`). The exact-head receipt records `factory-postgres-exit`, `factory-unit`, and `source-stability` as PASS. | PASS |

## Prior-suite regression coverage

- All 43 factory tests passed twice. This retains API/auth bounds, immutable intake, duplicate/change handling, API and command idempotency, empty-claim replay, same-key serialization, leased cancel/supersede release, claim contention, capacity ceilings, late fencing, retry/dead-letter behavior, budgets/accounting, kill switches, audit verification, role isolation, reconciliation replay, and actual restart.
- Migration discovery now requires contiguous versions 1 through 8, eight unique checksums, and the allocation-update revoke marker (`factory/tests/test_migrations.py:7-12`, `factory/tests/test_migrations.py:31-54`). Readiness requires schema version 8 (`factory/src/adaptive_factory/store.py:59-69`).
- Installer inventory explicitly asserts migration 008 is present (`tests/test_installer.py:155-175`). A newly materialized install built the package from its own path and passed the complete 43-test PostgreSQL exit suite.
- Capacity boundaries remain explicit rather than counter-only: repository task 11 stays unleased, global reader 21 returns no grant, and writer 2 returns no grant (`factory/tests/test_postgres_integration.py:428-471`).
- Idempotency remains behavior-bearing: response equality, changed-payload conflict, empty result persistence, replay-before-stale-fence, persisted correlations, and concurrency serialization are covered (`factory/tests/test_postgres_integration.py:211-367`).

## Test honesty and failure paths

- The new privilege test is not metadata-only: it checks `has_column_privilege` and executes both release and resurrection DML under the effective runtime role.
- The hidden-allocation setup intentionally uses the disposable database owner, not runtime, to simulate privileged corruption that runtime is now prohibited from creating. The tested service reconnects as `factory_runtime`, so the observed `FenceError` and reconciliation failures exercise production authority boundaries.
- The hidden-allocation test distinguishes fencing from generic failure by requiring `FenceError` separately for heartbeat, release, reserve-budget, and observe-usage. It also proves recovery after owner-side repair, preventing a false positive caused by an unusable normal path.
- Reconciliation checks counter/allocation consistency before idempotency replay or candidate repair and raises a specific `StoreError`, so inconsistent state cannot be silently skipped or recorded as a successful no-op.
- The exit runner fails nonzero on missing tooling, install/readiness failure, any test failure, or restart-probe failure. The restart probe restarts the actual database container rather than only reconstructing Python objects.
- Source-tree-only success is excluded by the second run: the installer materialized the exact managed payload, including migration 008 and all factory tests, and the installed path built and ran independently.

## Commands and evidence

```text
git rev-parse HEAD
  f82134de35e531a8b3bbf235ad480254ba40f1fe

git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..f82134de35e531a8b3bbf235ad480254ba40f1fe
  PASS (no output)

python3 factory/tests/run_disposable_exit.py
  PASS: 43 tests in 16.615s
  PASS: PostgreSQL restarted; one repair; replay no-op; higher fence; late holder rejected
  PASS: disposable PostgreSQL + API + effective roles + actual restart/reconciliation

python3 scripts/install_into.py --materialize-new /tmp/m4-r5-install.eBhlQl/installed
  PASS: verified payload materialized with migration 008, lockfile, exit runner, restart probe, and tests

(cd /tmp/m4-r5-install.eBhlQl/installed && python3 factory/tests/run_disposable_exit.py)
  PASS: package built from installed path
  PASS: 43 tests in 16.863s
  PASS: actual PostgreSQL restart; one repair; replay no-op; higher fence; late holder rejected

exact-head verification receipt inspection
  PASS: status=pass
  PASS: head=f82134de35e531a8b3bbf235ad480254ba40f1fe
  PASS: tree_fingerprint=e4ac983f20ea22120e98b5eb6597fa6d47486225000a29caf1ab45cadc726b6a
  PASS: git-diff-check, factory-unit, factory-postgres-exit, and source-stability
  factory-postgres-exit: 43 tests in 17.402s plus actual restart/reconciliation PASS
```

The materialized review install was moved to trash after testing and is recoverable there. Both exit runners removed their disposable containers. No shared, Trust CI, external, or production database was read or mutated.
