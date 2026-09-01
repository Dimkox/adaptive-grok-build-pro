# Data review — round 4

## Binding and verdict

- Route: `b7f288f1e81e`
- Base SHA: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Reviewed head SHA: `9fd2a56c57f834ad39c03a2f748bdbaefc79c91c`
- Full reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..9fd2a56c57f834ad39c03a2f748bdbaefc79c91c`
- Review role: route-selected read-only `data_reviewer`
- Round: final round / round 4
- Verdict: **FAIL**

Migration 007 fixes direct counter-policy mutation and the supported scheduler now enforces 20 global readers, 10 readers per repository, and one live writer. One Important allocation-authority defect remains: `factory_runtime` retains direct `UPDATE(released_at)` on `capacity_allocations`, can hide a live allocation outside the canonical release function, and leaves the control plane unable to reconcile while the worker remains live. Under the requested gate, an Important issue requires FAIL.

## Finding

### Important — runtime can still directly tamper with live capacity allocations and create unrecoverable drift

Migration 005 granted `factory_runtime` column update on `capacity_allocations.released_at` (`factory/src/adaptive_factory/resources/005_security_accounting_commands.sql:60-67`). Migration 007 revokes direct counter `INSERT, UPDATE` and allocation `INSERT`, but does not revoke allocation `UPDATE` (`factory/src/adaptive_factory/resources/007_capacity_authority.sql:160-169`). The store no longer needs this grant: normal close paths set the run closed and invoke the security-definer `capacity_release()` function, which alone updates allocation release time and counters together (`factory/src/adaptive_factory/resources/007_capacity_authority.sql:127-157`; `factory/src/adaptive_factory/store.py:528-579,617-677`).

Using the effective runtime role, a direct update of a live allocation's `released_at` succeeded. This creates four inconsistent views:

- the run and task remain leased, and `_lock_grant()` does not require `capacity_allocations.released_at IS NULL`, so the worker can continue heartbeating (`factory/src/adaptive_factory/store.py:581-615`);
- the allocation disappears from live-allocation metrics and readiness's allocation counts (`factory/src/adaptive_factory/store.py:61-106`);
- the global and repository counters remain at one because the canonical release function was bypassed;
- readiness becomes `not_ready`, while reconciliation fails before examining candidates because it detects the mismatch and provides no repair path (`factory/src/adaptive_factory/store.py:913-962`).

Fresh disposable PostgreSQL 17 evidence:

```text
runtime_capacity_privileges= (False, True, False)
direct_allocation_tamper_rows= 1
readiness_after_tamper= {'status': 'not_ready', 'database_role': 'factory_runtime', 'schema_version': 7, 'capacity_consistent': False}
reconcile_after_tamper= StoreError capacity counters do not match live allocations
live_worker_heartbeat_after_hidden_allocation= True
tampered_state= ('leased', True, False, 1)
```

The tuple in `runtime_capacity_privileges` is `(capacity_allocations INSERT, capacity_allocations.released_at UPDATE, capacity_counters.active_count UPDATE)`. Direct counter and allocation inserts are denied, but direct allocation release mutation is still allowed.

This violates AC-005's transactional capacity invariant, the mandatory least-privilege requirement, and the rollback/readiness condition requiring zero allocation imbalance (`engineering/changes/20260831-implement-a-new-m4-application-feature-on-exact-b7f288/requirements.md:9,26`; `engineering/changes/20260831-implement-a-new-m4-application-feature-on-exact-b7f288/rollback.md:3-5`). Fail-closed readiness is positive detection, but detection without a bounded repair path does not preserve the capacity authority and leaves a live worker outside the allocation view.

Required repair: add a forward migration revoking `UPDATE` on `factory.capacity_allocations` from `factory_runtime`; require all release mutation through `factory.capacity_release(uuid)`; extend the effective-role forbidden-DML test with direct `released_at` updates (including setting and clearing it). Keep readiness's consistency check, and add a reviewed owner/migrator repair procedure or a narrowly scoped canonical reconciliation function for legacy drift. `_lock_grant()` should also require the joined allocation to remain live so a hidden allocation cannot continue as an accepted worker lease.

## Prior findings rechecked

### PASS — canonical capacity policy and direct counter tampering denial

Migration 007 adds a schema constraint encoding exactly `global:reader=20`, `global:writer=1`, and `repository:<1..128 bytes>:reader=10` (`factory/src/adaptive_factory/resources/007_capacity_authority.sql:1-9`). It revokes runtime counter insert/update and grants only fixed-search-path security-definer functions for eligibility, allocation locking, allocation and release (`factory/src/adaptive_factory/resources/007_capacity_authority.sql:11-169`). Effective-role tests deny ceiling updates, active-count updates, and forged counter inserts (`factory/tests/test_postgres_integration.py:614-656`). The round-3 arbitrary ceiling/counter-reset exploits no longer succeed.

### PASS — supported scheduler caps 20 global readers, 10 per repository, one writer

Claims call `capacity_eligible_repositories()` before `FOR UPDATE SKIP LOCKED`, then create run/attempt and call `capacity_allocate()` in the same transaction (`factory/src/adaptive_factory/store.py:418-521`). Both functions lock canonical counters in stable order and `capacity_allocate()` rechecks every ceiling before inserting and incrementing (`factory/src/adaptive_factory/resources/007_capacity_authority.sql:11-53,80-125`). Fresh supported-path evidence:

```text
supported_reader_grants= 20 repo_a= 10 repo_b= 10
supported_writer_grants= 1 second_writer_none= True
readiness_at_caps= {'status': 'ready', 'database_role': 'factory_runtime', 'schema_version': 7, 'capacity_consistent': True}
canonical_capacity_rows= [('global:reader', 20, 20), ('global:writer', 1, 1), ('repository:repo/a:reader', 10, 10), ('repository:repo/b:reader', 10, 10)]
live_allocations_by_role= [('reader', 20), ('writer', 1)]
```

The partial unique live-writer index remains an independent one-writer backstop (`factory/src/adaptive_factory/resources/002_runs_leases_capacity.sql:54-55`).

### PASS — lease closure, orphan reconciliation, fencing and idempotency

Cancel, supersede, release and orphan repair now use capacity-lock/release functions and preserve the fixed lock order (`factory/src/adaptive_factory/store.py:523-579,617-688,913-982`). Clean-path consistency is checked before reconciliation; current and orphan expired runs are separated, and command replay remains actor/action/request/result bound (`factory/src/adaptive_factory/store.py:89-112,913-962`). Disposable tests for cancel/supersede release-once, mixed orphan/current reconciliation, stale fences, empty-claim replay and mutation replay passed. The Important direct-allocation mutation above is the remaining exception.

### PASS — accounting and immutable records

Reservation replay resolves before live-fence checks; changed commands are rejected; cost/token/wall reservations are bounded and settled transactionally into immutable usage observations; output limits and completion's settled-accounting requirement remain enforced (`factory/src/adaptive_factory/store.py:690-892,635-647`). Accepted intents, task events, usage observations, kill switches and audit rows remain denied runtime update, with lifecycle-only grants for task/run/attempt fields (`factory/src/adaptive_factory/resources/005_security_accounting_commands.sql:58-71`). Focused PostgreSQL accounting, completion, immutable-role and API replay tests passed.

### PASS — schema integrity, indexes, migrations and recovery posture

Composite `(run_id,task_id)` foreign keys cover allocations, reservations and usage, and audit rows reference runs (`factory/src/adaptive_factory/resources/005_security_accounting_commands.sql:43-53`). Repository listing and reconciliation keyset indexes match their bounded queries (`factory/src/adaptive_factory/resources/005_security_accounting_commands.sql:55-56`). Migrations remain contiguous 001–007, checksum-drift protected and applied in one advisory-locked transaction with timeouts (`factory/src/adaptive_factory/migrations.py:33-64,84-108`). Recovery remains forward-only; migration 007 introduces no destructive down migration.

## Commands and evidence

Binding/static checks:

```text
git rev-parse HEAD
# 9fd2a56c57f834ad39c03a2f748bdbaefc79c91c
git diff --name-status 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..9fd2a56c57f834ad39c03a2f748bdbaefc79c91c
git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..9fd2a56c57f834ad39c03a2f748bdbaefc79c91c
# exit 0
```

Fresh disposable PostgreSQL baseline:

```text
docker run --name m4-data-review-r4-b7f288 ... postgres:17-alpine
FACTORY_TEST_DATABASE_URL=<disposable-local-url> uv run --project factory python -m unittest factory.tests.test_postgres_integration -v
# Ran 12 tests in 15.645s — OK

uv run --project factory python -m unittest factory.tests.test_migrations -v
# Ran 4 tests in 0.006s — OK
```

The parent supplied fresh verifier PASS evidence for exact head `9fd2a56c57f834ad39c03a2f748bdbaefc79c91c`; this review independently reran the focused PostgreSQL and migration suites and the targeted effective-role probes. Owner access was used only to provision/truncate the fresh disposable database and assume `SET LOCAL ROLE factory_runtime`. All supported-path intake and claims used the service/store, whose connections enforce `SET ROLE factory_runtime` (`factory/src/adaptive_factory/store.py:50-65`). Exact probe outputs are quoted above.

The exact disposable container `m4-data-review-r4-b7f288` was removed after review; no shared, Trust CI, external, or production database was read or mutated. No product code was changed.

Because exact head `9fd2a56c57f834ad39c03a2f748bdbaefc79c91c` retains an Important allocation-authority defect, do not record a passing `data_review` receipt for this report.
