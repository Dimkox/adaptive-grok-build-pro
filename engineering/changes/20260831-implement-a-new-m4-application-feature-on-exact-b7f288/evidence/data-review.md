# Data review — round 3

## Binding and verdict

- Route: `b7f288f1e81e`
- Base SHA: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Reviewed head SHA: `8435e23458885a48e2d5784f8cd01e84d978c28c`
- Full reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..8435e23458885a48e2d5784f8cd01e84d978c28c`
- Review role: route-selected read-only `data_reviewer`
- Round: final round / round 3
- Verdict: **FAIL**

Migration 006 resolves direct updates to policy ceilings and intake identities, and the prior cancellation, accounting, immutable-update, cross-record FK, and keyset-index findings are repaired. However, one Important least-privilege/capacity defect remains and was reproduced through the effective runtime role plus the supported scheduler. Under the requested gate, an Important issue requires FAIL.

## Findings

### Important — the runtime role can create or falsify capacity policy state, and normal claims then exceed both hard reader caps

Migration 003 granted `factory_runtime` table-level `INSERT` and `UPDATE` on `capacity_counters` (`factory/src/adaptive_factory/resources/003_budgets_kills_reconciliation.sql:48-53`). Migration 006 revokes table-level update and restores column update only for `active_count`, but does not revoke `INSERT` (`factory/src/adaptive_factory/resources/006_runtime_policy_privileges.sql:1-2`). Consequently:

1. `factory_runtime` can insert a previously absent repository counter with any positive `ceiling` and any `active_count <= ceiling`. The schema constraint is only relational (`active_count <= ceiling`); it does not encode global reader 20, repository reader 10, or writer 1 (`factory/src/adaptive_factory/resources/002_runs_leases_capacity.sql:38-43`).
2. The supported claim path uses `INSERT ... ceiling=10 ON CONFLICT DO NOTHING`, then trusts the pre-existing row's ceiling (`factory/src/adaptive_factory/store.py:423-464`). A runtime-inserted `repository:repo/poisoned:reader` row with ceiling 999 therefore permits more than 10 live readers in that repository.
3. The column grant permits arbitrary assignment to `active_count`, not only the store's locked `+1`/`-1` transitions (`factory/src/adaptive_factory/store.py:495-501,577-581,683-689`). Resetting `global:reader.active_count` while 20 allocations remain lets the unchanged supported scheduler issue a 21st simultaneous global reader.
4. Reconciliation repairs expired allocations but does not derive/reconcile counters or ceilings from live allocations (`factory/src/adaptive_factory/store.py:947-994`). Metrics also trusts the mutable counters (`factory/src/adaptive_factory/store.py:67-86`). The false policy state therefore persists and hides the actual over-allocation.

This violates AC-005's database-enforced limits, the least-privilege requirement, and the rollback stop condition requiring zero leaked/imbalanced allocations (`engineering/changes/20260831-implement-a-new-m4-application-feature-on-exact-b7f288/requirements.md:9,26`; `engineering/changes/20260831-implement-a-new-m4-application-feature-on-exact-b7f288/rollback.md:3-5`). It is not merely hypothetical metadata drift: all 21 grants were created through `FactoryService.claim()`/`PostgresFactoryStore.claim()` after the runtime-role mutations.

Fresh disposable PostgreSQL 17 evidence:

```text
runtime_capacity_privileges= (True, False)
supported_claims_granted= 20 claim_21_is_none= True
capacity_rows= [('global:reader', 20, 20), ('repository:repo/poisoned:reader', 20, 999)]
live_repo_allocations= 20
runtime_reset_global_rows= 1
supported_21st_live_grant= True
capacity_rows_after_reset_claim= [('global:reader', 1, 20), ('repository:repo/poisoned:reader', 21, 999)]
live_global_reader_allocations= 21
```

The first phase proves runtime `INSERT` alone defeats the hard 10/repository cap while the immutable preseeded global row still stops at 20. The second phase proves the remaining arbitrary `active_count` update authority defeats the hard 20/global cap. The live-writer unique index still independently limits one live writer (`factory/src/adaptive_factory/resources/002_runs_leases_capacity.sql:54-55`), but that does not repair reader capacity.

Required repair: make policy values database-owned and make counter mutation capability-shaped rather than granting raw DML. At minimum, revoke direct runtime `INSERT` on `capacity_counters`, encode the only valid scope/ceiling combinations in database constraints, and expose repository-counter creation plus locked increment/decrement through tightly scoped functions or an equivalent mechanism that cannot assign arbitrary counts. Reconciliation/readiness must compare counters with live allocations and fail closed on any mismatch. Add effective-role tests that attempt arbitrary inserts and non-delta active-count assignments, then prove 11th repository and 21st global claims remain impossible after every allowed runtime operation.

## Prior findings rechecked

### PASS — leased cancellation/supersession, allocation release, and reconciliation isolation

`_close_active_lease()` now locks capacity in the same order as claim/release, closes run/attempt/allocation once, and decrements applicable counters before the task pointer is cleared (`factory/src/adaptive_factory/store.py:532-605`). Cancel and superseding intake call it before terminal projection changes (`factory/src/adaptive_factory/store.py:232-256,996-1015`). Reconciliation distinguishes current leases from orphan projections and repairs each idempotently (`factory/src/adaptive_factory/store.py:947-994`). The focused disposable test `test_cancel_and_supersede_release_leases_capacity_once` and mixed-orphan test passed.

### PASS — reservation replay, settled accounting, wall/cost/token/output bounds

Migration 005 adds task wall limits/reserved totals (`factory/src/adaptive_factory/resources/005_security_accounting_commands.sql:38-41`). Budget reservation replay is resolved before live-fence/budget evaluation, changed evidence is rejected, and reservation totals include observed cost/tokens plus reserved wall (`factory/src/adaptive_factory/store.py:724-789`). Observation releases the run's outstanding reservations transactionally before recording immutable observed totals; completion requires unblocked, present, settled accounting (`factory/src/adaptive_factory/store.py:791-926,660-672`). The focused reservation, accounting-command replay, overflow, and completion tests passed.

### PASS — immutable updates and command idempotency

Migration 005 replaces blanket updates with lifecycle-column grants and denies updates to accepted intents, task events, usage observations, kill switches, and audit rows (`factory/src/adaptive_factory/resources/005_security_accounting_commands.sql:58-71`). Migration 006 also removes intake-identity update. Effective-role mutation tests pass under actual `SET ROLE factory_runtime` (`factory/tests/test_postgres_integration.py:608-654`). Command outcomes are advisory-lock serialized and bound to actor/action/request digest/correlation/result (`factory/src/adaptive_factory/store.py:89-112`); focused API and accounting replay tests passed.

### PASS — composite integrity, migration history, and keyset indexes

Migration 005 adds composite `(run_id, task_id)` foreign keys for allocations, reservations and observations, plus the audit run FK (`factory/src/adaptive_factory/resources/005_security_accounting_commands.sql:43-53`). It adds `(repository_id, task_id)` task listing and `(task_id, lease_expires_at)` unreleased-run reconciliation indexes matching the bounded keyset queries (`factory/src/adaptive_factory/resources/005_security_accounting_commands.sql:55-56`). Migration discovery/checksum drift tests pass with contiguous versions 001–006, and migration application remains transaction/advisory-lock protected (`factory/src/adaptive_factory/migrations.py:33-64,84-108`). Recovery remains forward-only; no destructive rollback SQL was added.

### PASS with residual observation — locking and `SKIP LOCKED`

Claim still locks capacity rows in stable key order and selects one queued task with `FOR UPDATE SKIP LOCKED` (`factory/src/adaptive_factory/store.py:423-500`). Fences remain transactionally monotonic and subsequent mutations bind run/task/owner/fence/packet/live lease/deadline (`factory/src/adaptive_factory/store.py:465-530,607-623`). Reconciliation no longer uses `SKIP LOCKED` in its candidate query, but it re-locks each task/allocation through the fixed capacity-first order and the concurrent-safe close paths; no duplicate decrement or stale-fence failure was observed in the focused tests. This is not independently blocking in round 3.

## Commands and evidence

Binding/static checks:

```text
git rev-parse HEAD
# 8435e23458885a48e2d5784f8cd01e84d978c28c
git diff --name-status 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..8435e23458885a48e2d5784f8cd01e84d978c28c
git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..8435e23458885a48e2d5784f8cd01e84d978c28c
# exit 0
```

Fresh disposable PostgreSQL baseline:

```text
docker run --name m4-data-review-r3-b7f288 ... postgres:17-alpine
FACTORY_TEST_DATABASE_URL=<disposable-local-url> uv run --project factory python -m unittest factory.tests.test_postgres_integration -v
# Ran 12 tests in 15.187s — OK

uv run --project factory python -m unittest factory.tests.test_migrations -v
# Ran 4 tests in 0.005s — OK
```

Targeted probes used owner access only to provision/truncate the fresh disposable database and to assume `SET LOCAL ROLE factory_runtime`; every task intake and lease grant was then issued through the supported service/store path, whose connections themselves enforce `SET ROLE factory_runtime` (`factory/src/adaptive_factory/store.py:50-65`). Exact outputs are quoted in the Important finding. The disposable container `m4-data-review-r3-b7f288` was removed after review; no shared, Trust CI, external, or production database was read or mutated.

Because exact head `8435e23458885a48e2d5784f8cd01e84d978c28c` retains an Important database-policy defect, do not record a passing `data_review` receipt for this report.
