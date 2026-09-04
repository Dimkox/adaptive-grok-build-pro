# Final exact-head code review — M4 control plane

## Verdict

**PASS — no Critical or Important findings.**

The final M4 tree closes the prior authentication, snapshot-bounds, snapshot-consistency and stale-fence observability findings without changing the stable API/error contract. The PostgreSQL cutover, trigger/capability boundary, capacity-first lock order, final-postmaster readiness check, Bandit repair and M4→M9 documentation are coherent with the accepted scope and current repository state.

## Review binding

- Reviewer role: route-selected `code_reviewer`
- Route: `b7f288f1e81e`
- Accepted M3 base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Exact reviewed product commit: `4f75558770f2f332b32b4a47fe6afa61fcc524ec`
- Exact reviewed evidence HEAD: `9fe779ab9f90719201acfd01160d3452658ff075`
- Exact reviewed Git tree: `05707b35fb10ab9a29d3be35478faf4ef84789a1`
- Full reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..9fe779ab9f90719201acfd01160d3452658ff075`
- Exact verifier fingerprint: `2b9b3ee786663e3adba2e2f85e51e7c752c8e57166a0d7af6e3f62a88f4b45e8`
- Verifier receipt: **PASS**, 14/14 checks, created `2026-09-02T00:13:05+00:00`; root 488/488, factory unit 26/26, fresh disposable PostgreSQL 70/70, actual restart/reconciliation, Bandit, Ruff and source stability all passed.

The worktree was clean and exactly at the evidence HEAD before this report-only write.

## Critical and Important review

No Critical or Important defects remain.

### Migration 012, transactions and locking

- Migration `012` acquires write-conflicting locks on every source table used by the backfill before renaming the runtime-writable legacy counter table, creating the trusted singleton and scanning authoritative history. The migrator's transaction-local five-second lock and statement bounds make contention/oversized history leave the pre-apply state unchanged (schema `011` for the intended cutover); the documented rollout requires an operator-reviewed retry window.
- The trusted singleton is maintained by after-row triggers in the same transactions as task, event, run, allocation, usage, kill-head and completed-reconciliation changes. Historical fence values are correctly reset because pre-`012` runtime could forge them; the old rows remain revoked, preserved evidence.
- Runtime has no table DML/read access and no generic-key function. It may execute only the fixed snapshot reader and no-argument saturating fence increment. The snapshot read is one fixed-row statement under five-second statement and 500-millisecond lock bounds.
- Trigger acquisition is compatible with the established capacity-first mutation order: claims lock eligible capacity before inserting a run; release, cancel and reconciliation lock capacity before run/task counter changes; running reconciliation insertion deliberately avoids the singleton until the completed-state delta. The repaired deadlock regression and concurrent snapshot/release regression cover the relevant interleavings.

### Authentication, fences and error semantics

- The HTTP response-boundary middleware increments exactly once for every final 401/403, including invalid/missing credentials plus scope, actor-kind, repository and trusted-authority denials. The count is locked, saturating, process-local and label/credential free; tests cover all metrics authorization branches and restart reset.
- Store snapshot failure maps to bounded `503 metrics`; ordinary authorization and stale-fence mappings remain `403` and exact `409 {"error":"conflict","code":"stale_fence"}` respectively.
- Fence instrumentation runs only after the authoritative `FenceError`, uses a one-second connection bound plus shorter lock/statement bounds, suppresses only the best-effort observation failure, and re-raises the identical exception object. Unit fault injection and the locked-counter PostgreSQL/API test prove that the metric path neither replaces nor materially delays the stale-fence result.

### Compatibility, readiness and documentation

- The API stays version `1.0.0`; the metrics additions are an authenticated fixed-key surface and existing task/worker commands and error meanings remain compatible. No provider, repository, GitHub, Trust CI, deployment or external-write capability was introduced.
- The disposable exit waits for `postmaster.pid` to identify PID 1 and then requires `pg_isready`, distinguishing the official image's temporary bootstrap server from the final postmaster before opening host TCP. The exact verifier subsequently passed the fresh PostgreSQL exit and restart probe.
- Bandit now sees an explicit handled best-effort outcome rather than a silent exception; the exact configured Bandit gate and an independent focused Bandit run pass without a new suppression.
- README, factory README, roadmap, schedule, release, rollback and tasks consistently describe M4 as local/unaccepted, M5/M6 as provisional and dependency-restacked, M7-M9 as roadmap-only, the M5 rootless-host blocker, the `2026-09-08 00:00 UTC+3` hard deadline and the absence of external authority. The M4→M9 handoff table names bindings, gates/invalidation and rollback/forbidden authority. The decorative K22 graph contains exactly 22 nodes and 231 unique complete-pair edges and is explicitly not architecture or completion evidence.

## Independent checks during review

- `git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..9fe779ab9f90719201acfd01160d3452658ff075` — PASS.
- Focused API/migration/service suite in an isolated temporary environment — PASS, 23/23.
- `bandit -c bandit.yaml -q -r factory/src/adaptive_factory` — PASS.
- Focused Ruff check over factory source and reviewed tests — PASS.
- K22 exact node/edge set check — PASS, 22 nodes / 231 unique edges / zero missing or extra.
- Architecture validate, drift and diagram check — PASS with no findings or mismatches.
- Verification receipt inspection confirmed exact HEAD, exact fingerprint, all 14 passing gates and source stability.

This reviewer changed only this report. No product, contract, migration, test, architecture, governance, receipt, Git history or external state was modified. The report write necessarily changes the worktree fingerprint; a fresh receipt must bind the subsequently committed final evidence tree before local completion.
