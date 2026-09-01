# Final data re-review — exact HEAD `83e6b0d0c29e813932aa29b0d72ac4d85d27df7b`

## Binding and verdict

- Route: `b7f288f1e81e`
- Accepted base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Prior fix HEAD: `4230dc8e73bcf4dfcf6c60d294d379d44a30c698`
- Reviewed product HEAD: `83e6b0d0c29e813932aa29b0d72ac4d85d27df7b`
- Focused range: `4230dc8e73bcf4dfcf6c60d294d379d44a30c698..83e6b0d0c29e813932aa29b0d72ac4d85d27df7b`
- Supplied verifier result: PASS, fingerprint `9a9dd64921cc5edf8889330b79732016c0235cc37e4a27c712a05128b3659746`
- Review role: route-selected read-only `data_reviewer`
- Verdict: **FAIL**

The authority, mandatory-cleanup, current retry/completion, lock-order and index repairs are effective. Two Important schema-008 forward-recovery findings remain. No Critical finding was found.

## Findings

### Important — schema-008 blocked retry state is not quarantined and permanently fails readiness

Migration 010 quarantines a `queued`/`retry` task only when it has an active reservation or nonzero reserved aggregate (`factory/src/adaptive_factory/resources/010_authority_accounting_and_cleanup.sql:41-70`). It omits `task.accounting_blocked=true` from both update predicates. Readiness independently rejects every claimable blocked task (`factory/src/adaptive_factory/store.py:80-93`), while claim correctly excludes it (`factory/src/adaptive_factory/store.py:513-520`). There is no supported runtime path that converts this pre-existing retry projection to explicit accounting recovery.

This state is reachable in schema 008: missing/invalid pricing marks the leased task accounting-blocked, and a subsequent retryable release with no live reservation could persist `retry`, zero reserved counters and `accounting_blocked=true`. An independent PostgreSQL 17 probe built a non-empty schema-008 database with that state, applied exact packaged migrations 009 and 010, then connected through the runtime store:

```text
legacy_blocked_after_010=('retry', True, 0, 0, 0)
readiness={'status': 'not_ready', 'schema_version': 10,
           'capacity_consistent': True, 'accounting_consistent': False}
```

The claim defense prevents unsafe work, but the documented rollout cannot reach readiness and the migration has not provided bounded forward recovery. Direct owner mutation would be an undocumented security-sensitive recovery step.

Required repair: add a forward migration that quarantines every claimable `queued`/`retry` row with `accounting_blocked=true`, including zero-reservation/zero-aggregate rows, while preserving accounting and audit evidence. Add a real 008-to-current regression proving `needs_human`, ready service status, no claim, and idempotent re-application/restart behavior.

### Important — schema-008 positive terminal tasks can retain live prior-attempt reservations while readiness reports ready

The original cross-attempt bug could progress farther than `retry`: schema 008 completion checked active reservations only for the completing run, not the whole task. A reservation left live by attempt 1 could therefore survive attempt 2 completion and commit the positive terminal state `ready_for_human`. Migration 010 limits both quarantine updates to `state IN ('queued','retry')` (`010_authority_accounting_and_cleanup.sql:55,65`), and `_accounting_consistent()` uses the same state restriction (`store.py:83-91`). The current completion guard prevents new instances, but neither migration nor readiness repairs or exposes already durable instances.

An independent PostgreSQL 17 probe constructed the exact producible schema-008 history: failed released attempt 1 with an active reservation and nonzero task aggregates, completed attempt 2 with usage, and task state `ready_for_human`. After applying migrations 009 and 010:

```text
applied_versions=[9, 10]
legacy_ready_after_010=('ready_for_human', False, 500, 600, 700, 1)
readiness={'status': 'ready', 'schema_version': 10,
           'capacity_consistent': True, 'accounting_consistent': True}
```

This is a false positive at M4's sole successful endpoint: unresolved reserved budget survives upgrade and restart, yet the service advertises ready. The checked-in upgrade regression seeds only `retry`, so its PASS cannot cover the original bug's terminal outcome.

Required repair: make the forward migration and readiness invariant account for active reservations/aggregate disagreement in legacy positive terminal projections. The repair must preserve run/reservation/usage history and handle active-generation uniqueness when selecting an evidence-preserving exception state. Add a real 008-to-current regression for the two-attempt `ready_for_human` history and prove the unsafe positive endpoint cannot survive or be reported ready.

## Original and residual findings rechecked

- **Authority TOCTOU closed:** migration 010 replaces both fixed-search-path `SECURITY DEFINER` validators with `FOR SHARE`, which conflicts with the non-key `revoked_at` update. PostgreSQL tests cover observation and exception forms with revocation before validation (intake rejected) and after validation (revoker waits through intake commit, later intake rejected). PUBLIC execute remains revoked and runtime receives only the explicit execute grants (`010_authority_accounting_and_cleanup.sql:1-36`; `factory/tests/test_postgres_integration.py:235-316`).
- **Claim defense and current accounting closed:** claim now requires unblocked zero aggregates and no active task reservation. Failure with an active current reservation goes to `needs_human`; completion checks every active task reservation and all reserved aggregates. The checked-in non-empty 008 upgrade correctly quarantines its seeded active-reservation `retry` row. The incomplete historical state coverage is limited to the two findings above (`store.py:513-520,697-725`; integration test lines 960-1098).
- **Exhausted event cleanup closed:** ordinary events are counted separately from `mandatory_cleanup` facts. Release converts an exhausted retry to `needs_human`; release, expired-run reconciliation and cancel close run/allocation/counters once and append both a mandatory event and hash-chained audit in the same transaction. Exact replay/no-op checks pass (`store.py:192-231,622-647,729-759,1048-1068`; integration test lines 840-955).
- **Lock ordering closed:** reconcile, cancel, supersede and release acquire canonical capacity locks before task/run locks. The reproduced reconcile/cancel interleaving now completes without deadlock or double release (`store.py:590-620,1008-1041`; integration test lines 1190-1230).
- **Task-scoped indexes closed:** migrations retain predicate-compatible `audit_log_task_order`, `usage_observations_task_run`, `budget_reservations_task_run_active`, claim and reconciliation indexes. The populated `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` regression requires the named indexes and passed (`009_authority_audit_and_history_indexes.sql:25-30`; integration test lines 1232-1275).

## Migration, roles, audit and restart assessment

- Packaged migrations are contiguous `001..010`; the planner rejects non-contiguous history, missing package history and checksum drift. Migrations 001-009 are unchanged in the focused range; packaged migration 009 still hashes to `2e37378af506bf18ab11705430b6876136ac3918d3d1e5699e7d63848b946e6a`. Migration 010 is additive/forward-only and applies atomically under the migrator advisory lock and five-second transaction limits.
- Migration 010's new event column inherits the established table privileges. Runtime still cannot update/delete append-only audit/events, mutate capacity policy/counters directly, release allocations directly, or access the separate `trust_ci` schema. The disposable effective-role and shipped bootstrap tests passed.
- Audit v1 history remains verifiable; all new v2 rows bind task/run/correlation identity. Mandatory cleanup includes the event and v2 audit fact transactionally. Capacity release remains capability-shaped, lock ordered, underflow checked and exactly once.
- Actual PostgreSQL restart evidence passed: one expired lease repair, zero-repair replay, higher fence and late-holder rejection. The remaining defects are migration/readiness coverage of already durable schema-008 accounting state, not volatile restart state.

## Verification evidence

- `git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..83e6b0d0c29e813932aa29b0d72ac4d85d27df7b` — PASS.
- `python3 factory/tests/run_disposable_exit.py` — PASS: 63/63 tests in 33.968s, effective roles, both authority forms/interleavings, accounting/retry boundaries, exhausted-event release/reconcile/cancel, deadlock regression, indexed plans, actual PostgreSQL restart and reconciliation.
- Independent non-empty 008-to-010 blocked-retry probe — FAIL as described above.
- Independent non-empty 008-to-010 two-attempt positive-terminal reservation probe — FAIL as described above.
- The exact disposable container `adaptive-factory-data-final-83e6b0d` and temporary environment were removed after review. No shared, external, Trust CI or production database was read or mutated.

No product file, commit or review receipt was changed. Only this report was overwritten.

**Final data-review result: FAIL for exact product HEAD `83e6b0d0c29e813932aa29b0d72ac4d85d27df7b`.**
