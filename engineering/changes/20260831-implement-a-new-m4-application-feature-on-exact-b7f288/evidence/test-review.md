# Final exact-head independent test review — M4 durable factory control plane

## Verdict

**PASS**

- Reviewer role: route-selected read-only `test_reviewer`
- Route: `b7f288f1e81e`
- Accepted M3 base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Exact reviewed evidence HEAD: `9fe779ab9f90719201acfd01160d3452658ff075`
- Exact reviewed Git tree before this report write: `05707b35fb10ab9a29d3be35478faf4ef84789a1`
- Exact reviewed product commit: `4f75558770f2f332b32b4a47fe6afa61fcc524ec`
- Full reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..9fe779ab9f90719201acfd01160d3452658ff075`
- Exact verifier tree fingerprint: `2b9b3ee786663e3adba2e2f85e51e7c752c8e57166a0d7af6e3f62a88f4b45e8`

No Critical or Important test/evidence gap remains. The final wave directly covers migration 012 privileges, trusted backfill, concurrency, snapshot consistency, upgrade/replay, timeout and fence-lock behavior; the complete HTTP authorization matrix; final-PID1 PostgreSQL readiness; the repaired Bandit path; K22 documentation/graph integrity; and the required negative/non-vacuous paths.

## Findings

No Critical or Important findings.

## Migration 012 and PostgreSQL validity

The inspected tests exercise behavior against disposable PostgreSQL rather than accepting SQL markers alone:

- `test_metric_counter_runtime_is_capability_only_monotonic_and_saturating` proves the effective runtime role cannot select, insert, update or delete the trusted singleton, cannot read or mutate the quarantined pre-012 table, cannot execute internal trigger functions, and can execute only the two fixed public capabilities. Eight concurrent supported increments must return eight distinct monotonic values `1..8`; a separate boundary assertion proves saturation at bigint maximum.
- `test_metrics_snapshot_is_atomic_constant_row_and_timed` uses a two-thread barrier around the actual snapshot query and a concurrent lease release. It accepts only the two coherent states `(live_leases,active_capacity)=(1,1)` or `(0,0)`, requires exactly one data `SELECT` through `read_metrics_snapshot()`, proves the plan reads one singleton row, verifies the exact `5s` statement and `500ms` lock bounds, and holds an exclusive table lock to require an HTTP 503 in under two seconds.
- `test_schema_008_upgrade_quarantines_legacy_reservation_before_claim` builds a non-empty schema-008 database, applies exactly migrations 009-012, preserves/quarantines legacy accounting states, rejects readiness inconsistencies, keeps the active generation claimable, derives the trusted snapshot from authoritative tables, retains forged legacy counters only as inaccessible untrusted evidence, and then requires a second migrator apply to return the empty tuple.
- `test_locked_metric_counter_never_delays_or_masks_stale_fence_409` holds the trusted counter row lock while issuing a real stale-fence HTTP heartbeat. The request must return the exact `409 {"error":"conflict","code":"stale_fence"}` in under one second with no counter change; after unlock the same authoritative error remains and the supported counter advances exactly once.
- `test_reconcile_and_cancel_share_capacity_then_task_lock_order` holds the shared capacity lock, overlaps cancel and reconcile in separate workers, and requires both to finish without deadlock and the task to reach `cancelled`. This directly covers the migration-012 reconciliation-trigger repair that avoids taking the singleton before the established capacity/task order.

The release inventory test is also state-changing and non-vacuous: it submits five task histories, drives three failures to retry/dead, reserves exact cost/token/wall values, records exact observed usage, expires and reconciles a lease, causes a real fence rejection, enables a kill, and then asserts fixed family/key sets plus exact values. It does not insert the expected trusted metric row directly.

## HTTP authorization, error preservation and readiness

`test_metrics_counts_auth_rejections_without_exposing_credentials` requires the complete final response matrix:

```text
missing bearer / invalid bearer / missing scope / repository-scoped operator / wrong actor kind
401            / 401            / 403           / 403                        / 403
```

The next authorized wildcard-operator response must report `auth_rejected=5`; actor IDs, repository identity and all four credentials must be absent; the response stays at most 2 KiB; and a fresh application instance must restart the explicitly process-local count at zero. `test_authenticated_request_reaches_real_unix_socket` independently proves the missing-auth and authorized paths through an actual Unix socket.

`test_fence_metric_failure_never_replaces_authoritative_fence_error` injects a store whose heartbeat raises one exact `FenceError` object and whose best-effort metric write fails. The service must re-raise the identical object. The final implementation's explicit `False` return closes Bandit B110 without widening the exception boundary or changing the authoritative error.

`test_exit_runner_waits_for_final_pid1_postmaster_and_readiness` covers both branches of the readiness helper: it requires the `postmaster.pid` first line to identify PID 1 before invoking `pg_isready`, and proves a non-final postmaster short-circuits without readiness acceptance. More importantly, the exact verifier's fresh PostgreSQL-17 exit ran the repaired helper end to end before all 70 database/API tests and the actual restart probe, so the unit test is not the only evidence for the image handoff.

## K22 graph and documentation evidence

`test_readme_stack_graph_is_complete` enumerates all 22 named nodes, requires every unordered pair to appear in either direction, extracts the Mermaid block and requires exactly `C(22,2)=231` edge lines. This prevents a missing pair, a short graph or an extra edge from passing. The README explicitly labels K22 a decorative inventory regression rather than architecture authority. Root README, roadmap, factory README and the active release/rollback/schedule/tasks package consistently record the M4→M5→M6 restack order, provisional downstream branches/routes, the M5 rootless-host blocker, the `2026-09-08 00:00 UTC+3` deadline without gate waiver, and the roadmap-only M4→M9 bindings/rollback/forbidden-authority boundaries.

## Exact verification and independent spot checks

The inspected fingerprint-bound verification receipt was created at `2026-09-02T00:13:05Z`, names architecture head `9fe779ab9f90719201acfd01160d3452658ff075`, and reports:

```text
14/14 verifier checks: PASS
root python-unittest: 488 tests in 496.646s — OK
factory-unit: 26 tests in 0.015s — OK
factory-postgres-exit: 70 tests in 41.360s — OK
actual restart: one repair; replay no-op; higher fence; late holder rejected — PASS
Bandit / Ruff / secret scan / SQL safety / architecture / governance: PASS
source stability: repository fingerprint remained stable — PASS
```

The receipt's PostgreSQL stderr lists every migration/snapshot/lock/auth/readiness test above as executed and passing. The implementation ledger also preserves the preceding RED evidence: arbitrary runtime metric access, mixed snapshots, unbounded fence-lock delay, reconciliation deadlock, Bandit B110 and temporary-postmaster handoff failure all reproduced before their repairs.

Independent review spot checks on the clean reviewed tree passed the exact Bandit command, the K22 completeness test, all migration/service tests that do not require project dependencies, and then the isolated-project authorization/readiness/error-preservation trio 3/3. A mixed host-Python invocation passed its dependency-free cases but could not import FastAPI because FastAPI is intentionally absent from the host environment; rerunning the affected case in the locked factory project environment passed without source or dependency changes.

`git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..9fe779ab9f90719201acfd01160d3452658ff075` produced no output. Before this report write, `git status --short` was empty and `HEAD`/`HEAD^{tree}` matched the exact evidence SHA/tree above.

This review changed only `test-review.md`. It did not modify product code, receipts, Git history, databases, external systems, production or Trust CI state. Writing the report changes the worktree fingerprint; the coordinator must bind the final review/verification receipts to the resulting final tree before claiming local closure.
