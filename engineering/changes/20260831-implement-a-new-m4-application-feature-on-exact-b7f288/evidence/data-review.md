# M4 final exact-head data review — PASS

## Review binding

- Route: `b7f288f1e81e`
- Change: `20260831-implement-a-new-m4-application-feature-on-exact-b7f288`
- Accepted M3 base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Exact reviewed product commit: `4f75558770f2f332b32b4a47fe6afa61fcc524ec`
- Exact reviewed clean evidence HEAD: `9fe779ab9f90719201acfd01160d3452658ff075`
- Evidence-head Git tree: `05707b35fb10ab9a29d3be35478faf4ef84789a1`
- Full reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..9fe779ab9f90719201acfd01160d3452658ff075`
- Exact verifier fingerprint: `2b9b3ee786663e3adba2e2f85e51e7c752c8e57166a0d7af6e3f62a88f4b45e8`
- Reviewer: route-selected read-only `data_reviewer`

The verifier receipt is PASS and binds the exact clean evidence HEAD and fingerprint above. Commits after the product commit contain evidence only. Concurrent final reviewers later rewrote only their own reports; those worktree changes were excluded from this product review.

## Verdict

**PASS — no Critical or Important data findings.**

- Critical data findings: **0**
- Important data findings: **0**

The previous DATA-006 torn-snapshot and DATA-007 unbounded-history-scan findings are closed by migration `012` and the single-row read path.

## Migration and rollup review

- Packaged migrations are contiguous `001..012`, checksum locked, validated against recorded name/version/hash and applied atomically under the factory advisory transaction lock. Migration `012` hashes to `887e59f809d5f4d31c619eccd568c35ced18a98fe047814f6020b91d28d5f2ce`.
- Migration `012` takes explicit write-conflicting locks on every authoritative source used by the backfill before renaming the runtime-writable legacy counter table, constructing the new singleton, backfilling it and installing triggers. Its five-second migration lock/statement bounds make failure atomic and retryable; the documented rollout schedules this cutover before service start and requires operator review on timeout.
- The backfill covers task totals/states/accounting, events, live/reclaimed runs, live allocations, usage output, latest kill heads and completed reconciliation totals. The pre-`012` fence value is intentionally reset because runtime could forge it; old rows are preserved as `metric_counters_pre_012_untrusted` with runtime/PUBLIC access revoked.
- Row triggers maintain signed old/new deltas in the same transactions as authoritative writes. Kill history uses a deterministic `(created_at,switch_id)` head and updates the active-kill gauge only when that head changes. Fence rejection uses a closed SECURITY DEFINER capability, atomic update and signed-bigint saturation.
- The singleton primary key/check guarantees at most one trusted rollup row; runtime has no direct SELECT/INSERT/UPDATE/DELETE on it or the quarantined legacy table. Runtime receives only the two fixed-search-path capabilities needed to read the snapshot and increment fence rejection; trigger functions and backing tables remain unavailable.
- Supported mutation paths retain capacity/allocation-before-run/task locking where lease closure needs it. The new triggers acquire only the one rollup row and do not introduce a second rollup lock order. Concurrent fence increments and live-lease/capacity transitions are covered by real PostgreSQL tests; no Critical/Important deadlock or lost-update path was found.

## Snapshot and query bounds

- `metrics()` sets transaction-local `statement_timeout='5s'` and `lock_timeout='500ms'`, then issues exactly one data statement through `read_metrics_snapshot()`; the SECURITY DEFINER function rejects absent or weaker bounds.
- The response reads one fixed row. It performs no scrape-time scan of `tasks`, `task_events`, `runs`, `usage_observations` or reconciliation history, so retained history no longer controls polling work.
- Because every authoritative delta and the singleton update commit in the same transaction, related values such as live leases and active capacity cannot be combined across commits. The two-connection barrier regression accepts only `(1,1)` or `(0,0)` and proves one SQL data statement.
- A conflicting table lock returns the authenticated metrics endpoint as bounded `503` in under two seconds. Best-effort fence accounting uses one-second connect, 100-millisecond lock and 250-millisecond statement bounds and cannot delay or replace the authoritative stale-fence `409`.

## Upgrade, replay, bootstrap and restart

- The real schema-008 fixture upgrades through `[009,010,011,012]`, preserves reservation/run/attempt/usage evidence, quarantines unsafe generation 1, keeps same-identity generation 2 uniquely claimable and reconstructs trusted metrics from authoritative tables rather than legacy counter input.
- Reapplying migrations returns no pending work. Bootstrap validates the distinct owner/runtime DSNs, effective `factory_runtime` role and exact schema `012` readiness.
- Readiness still verifies exact migration count plus capacity/allocation and claimable/accounting agreement. The disposable exit runner now waits for both official-image final postmaster PID 1 and `pg_isready`, eliminating bootstrap-postmaster handoff races.
- The actual restart probe preserves durable state, repairs exactly one expired lease, makes the second reconciliation a no-op, issues a higher fence and rejects the late holder.

## Verification evidence

- Exact receipt created `2026-09-02T00:13:05Z`: all 14 gates PASS, including source stability on fingerprint `2b9b3ee786663e3adba2e2f85e51e7c752c8e57166a0d7af6e3f62a88f4b45e8`.
- Fresh disposable PostgreSQL 17 exit recorded **70/70 PASS in 41.360s**, followed by PASS for actual restart, one repair, replay no-op, higher fence and late-holder rejection; the exact disposable container was removed.
- Reviewer-focused `factory.tests.test_migrations` plus `factory.tests.test_service`: **13/13 PASS**.
- `git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..9fe779ab9f90719201acfd01160d3452658ff075`: PASS.

This reviewer changed only this report. No product, migration, test, receipt, Git history, database or external state was modified. Writing review evidence changes the worktree fingerprint, so final receipt recording must bind the subsequently committed evidence tree.

**Final data-review result: PASS for product commit `4f75558770f2f332b32b4a47fe6afa61fcc524ec` on clean evidence HEAD `9fe779ab9f90719201acfd01160d3452658ff075`.**
