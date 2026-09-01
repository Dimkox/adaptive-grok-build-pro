# Data review — round 5

## Binding and verdict

- Route: `b7f288f1e81e`
- Base SHA: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Reviewed head SHA: `f82134de35e531a8b3bbf235ad480254ba40f1fe`
- Full reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..f82134de35e531a8b3bbf235ad480254ba40f1fe`
- Review role: route-selected read-only `data_reviewer`
- Round: final round / round 5
- Verdict: **PASS**

No Critical or Important data finding remains. Migration 008 revokes the last direct runtime allocation-mutation privilege, worker fencing now requires a live allocation, and inconsistent capacity state makes readiness and reconciliation fail closed. All prior capacity, schema-integrity, accounting, idempotency, reconciliation, index and migration findings were rechecked against a fresh disposable PostgreSQL 17 database.

## Round-5 delta

### PASS — allocation release is canonical and direct runtime tampering is denied

Migration 008 revokes all runtime update authority on `factory.capacity_allocations` (`factory/src/adaptive_factory/resources/008_allocation_release_authority.sql:1`). Migration 007 already revoked direct allocation insert and counter insert/update, constrained canonical ceilings, and exposed only fixed-search-path security-definer capacity functions (`factory/src/adaptive_factory/resources/007_capacity_authority.sql:1-169`). Effective runtime permissions are now:

```text
runtime_capacity_mutation_privileges= (False, False, False)
runtime_allocation_tamper=InsufficientPrivilege
```

The tuple is `(capacity_allocations.released_at UPDATE, capacity_allocations INSERT, capacity_counters.active_count UPDATE)`. Normal store paths no longer require allocation-row update locks or DML: they lock run/task rows, close the run, and invoke `capacity_release()` to atomically release allocation plus counters (`factory/src/adaptive_factory/store.py:523-579,618-677`). The focused effective-role suite also denies allocation `released_at` updates in both directions (`factory/tests/test_postgres_integration.py:614-659`).

### PASS — hidden/mismatched allocations invalidate worker fences and fail closed

`_lock_grant()` now requires `capacity_allocations.released_at IS NULL`, so heartbeat, release, budget reservation and usage observation all reject a grant whose allocation is absent or hidden (`factory/src/adaptive_factory/store.py:581-598`). Readiness requires schema version 8 and exact counter/live-allocation equality, while reconciliation refuses to operate on inconsistent capacity authority (`factory/src/adaptive_factory/store.py:61-85,914-963`). An owner-only corruption probe produced:

```text
heartbeat_hidden=FenceError
release_hidden=FenceError
reserve_hidden=FenceError
observe_hidden=FenceError
readiness_hidden= {'status': 'not_ready', 'database_role': 'factory_runtime', 'schema_version': 8, 'capacity_consistent': False}
reconcile_hidden= StoreError capacity counters do not match live allocations
```

After owner restoration of the simulated legacy drift, the normal accounting/release path completed and readiness recovered:

```text
release_restored= ready_for_human
readiness_restored= {'status': 'ready', 'database_role': 'factory_runtime', 'schema_version': 8, 'capacity_consistent': True}
```

The checked-in regression covers heartbeat, failure release, reservation and observation fencing, fail-closed readiness/reconciliation, owner restoration and canonical completion (`factory/tests/test_postgres_integration.py:670-718`).

## Prior findings rechecked

### PASS — database-enforced scheduler capacity 20 global readers / 10 per repository / one writer

The canonical policy constraint encodes only global reader 20, global writer 1 and repository reader 10 rows (`factory/src/adaptive_factory/resources/007_capacity_authority.sql:1-9`). Eligibility and allocation functions lock counters in stable order and recheck every ceiling before allocation/counter increment (`factory/src/adaptive_factory/resources/007_capacity_authority.sql:11-53,80-125`). Claims use those functions around `FOR UPDATE SKIP LOCKED` task selection in one transaction (`factory/src/adaptive_factory/store.py:418-521`). The fresh integration suite proves exactly 20 readers overall, 10 in each of two repositories, and one writer; the partial unique live-writer index remains an independent backstop (`factory/src/adaptive_factory/resources/002_runs_leases_capacity.sql:54-55`).

### PASS — lease closure, monotonic fencing, retries and reconciliation

Cancel, supersede, release and orphan repair use the same capacity-first lock/release authority and are idempotent (`factory/src/adaptive_factory/store.py:523-579,618-688,914-983`). Per-task fence sequences remain transactionally monotonic; task/run/owner/fence/packet/live allocation/live lease/deadline predicates reject stale work (`factory/src/adaptive_factory/store.py:450-521,581-598`). Reconciliation is bounded to 100, five seconds, ordered by task keyset, separates current expired leases from orphan projections, and rejects capacity drift before mutation (`factory/src/adaptive_factory/store.py:914-963`). Focused cancel/supersede, mixed orphan/current, restart, stale-fence and retry/DLQ tests passed.

### PASS — accounting budgets and mutation idempotency

Command results are advisory-lock serialized and bound to actor, action, canonical request digest, correlation and exact result (`factory/src/adaptive_factory/store.py:109-132`). Reservation replay resolves before live-fence checks; changed evidence is rejected; cost/token/wall reservations are bounded and settled transactionally into immutable usage; output limits and completion's settled-accounting requirement remain enforced (`factory/src/adaptive_factory/store.py:690-892,635-647`). Focused API mutation replay, accounting replay after stale fence, reservation settlement, missing accounting and completion tests passed.

### PASS — immutable evidence and relational constraints

Accepted intents and task events remain insert-only for runtime; audit and usage evidence cannot be updated; task/run/attempt updates are restricted to required lifecycle columns (`factory/src/adaptive_factory/resources/005_security_accounting_commands.sql:58-71`; `factory/src/adaptive_factory/resources/006_runtime_policy_privileges.sql:1-2`; `factory/src/adaptive_factory/resources/008_allocation_release_authority.sql:1`). Composite `(run_id,task_id)` foreign keys cover allocations, reservations and observations, and audit rows reference runs (`factory/src/adaptive_factory/resources/005_security_accounting_commands.sql:43-53`). Effective-role mutation tests and hash-chain verification passed.

### PASS — indexes, migrations and recovery posture

Repository listing uses `(repository_id,task_id)` and reconciliation uses the unreleased `(task_id,lease_expires_at)` keyset index (`factory/src/adaptive_factory/resources/005_security_accounting_commands.sql:55-56`; `factory/src/adaptive_factory/store.py:338-354,925-930`). Migrations are contiguous 001–008, checksum-drift protected and applied under one transaction-scoped advisory lock with lock/statement timeouts (`factory/src/adaptive_factory/migrations.py:33-64,84-108`). Migration 008 is a forward-only least-privilege contraction and introduces no destructive data rewrite or down migration. Recovery remains preserve/restore-forward-fix rather than destructive rollback.

## Commands and evidence

Binding/static checks:

```text
git rev-parse HEAD
# f82134de35e531a8b3bbf235ad480254ba40f1fe
git diff --name-status 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..f82134de35e531a8b3bbf235ad480254ba40f1fe
git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..f82134de35e531a8b3bbf235ad480254ba40f1fe
# exit 0
```

Fresh disposable PostgreSQL evidence:

```text
docker run --name m4-data-review-r5-b7f288 ... postgres:17-alpine
FACTORY_TEST_DATABASE_URL=<disposable-local-url> uv run --project factory python -m unittest factory.tests.test_postgres_integration -v
# Ran 13 tests in 16.947s — OK

uv run --project factory python -m unittest factory.tests.test_migrations -v
# Ran 4 tests in 0.005s — OK
```

The parent supplied fresh verifier plus independent code/test/security PASS evidence for exact head `f82134de35e531a8b3bbf235ad480254ba40f1fe`. This review independently reran the full PostgreSQL integration suite, migration suite, static diff check and targeted effective-role/fencing probes. Owner access was used only to provision/truncate the disposable database and simulate/restore legacy corruption; supported product operations ran through service/store connections that enforce `SET ROLE factory_runtime` (`factory/src/adaptive_factory/store.py:50-59`).

The exact disposable container `m4-data-review-r5-b7f288` was removed after review; no shared, Trust CI, external or production database was read or mutated. No product code was changed.

**Final data-review result: PASS for exact head `f82134de35e531a8b3bbf235ad480254ba40f1fe`.**
