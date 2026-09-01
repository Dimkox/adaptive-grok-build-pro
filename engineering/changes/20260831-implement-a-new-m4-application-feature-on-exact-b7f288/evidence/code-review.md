# Final exact-head code review — M4 metrics closure

## Verdict

**FAIL — three Important correctness and operability findings remain.**

The fixed response keys are low-cardinality and redacted, the scanner-only fixture change preserves runtime authentication behavior, and the earlier M4 authority/accounting/capacity fixes remain intact. However, the promised authentication signal is incomplete, the metrics read is neither work-bounded nor snapshot-consistent, and synchronous fence instrumentation can replace the stable stale-fence API result.

## Review binding

- Reviewer role: route-selected `code_reviewer`
- Route: `b7f288f1e81e`
- Accepted M3 base and exact merge base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Exact reviewed product HEAD: `fa043d48430963f82c52a76fbdabe2c35cd3d995`
- Exact reviewed Git tree: `d8024cc0a188b4d58006a87fca5685e66471346a`
- Metrics repair commit: `034168b5e5d38544cc8388c892e61918b91d1e8f`
- Scanner-fixture commit: `fa043d48430963f82c52a76fbdabe2c35cd3d995`
- Full reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..fa043d48430963f82c52a76fbdabe2c35cd3d995`
- Exact-head verifier before review-report writes: **PASS**, all 14 gates, created `2026-09-01T22:57:57+00:00`, fingerprint `9ec2ce27d8dd0e0ee896573d282f4e0dcef2349a05914659d9bdac1e8dc37d75`.

## Important findings

### CR-004 — valid-token metrics authorization rejections are not counted

`Authenticator.authenticate()` increments `auth_rejected` only for a missing/malformed bearer value, an unknown token, or a token missing `factory:reconcile` (`factory/src/adaptive_factory/api.py:56-73`). `FactoryService.metrics()` then performs two additional authorization checks — actor kind must be `operator` and repository authority must contain `*` — after authentication has succeeded (`factory/src/adaptive_factory/service.py:31-35`). Those 403 paths never call `_reject()`.

This is reachable configuration, not only a synthetic direct-call state: `load_actors()` accepts any closed combination of valid kind, scopes and repositories and does not require a reconcile actor to be a wildcard operator (`factory/src/adaptive_factory/server.py:34-56`). An actual `TestClient` reproduction on this exact HEAD used a valid operator token with `factory:reconcile` and `repositories={"owner/repo"}`. `/metrics` returned 403, but the next authorized wildcard poll returned `auth_rejected: 0`:

```text
{'rejected_status': 403, 'auth_rejected': 0}
```

The new regression covers only a token with no reconcile scope (`factory/tests/test_api.py:139-163`), so it misses both post-authentication rejection branches. This violates the release finding's required unauthorized-access signal and the shipped statement that authentication rejections are counted. A valid but mis-scoped or wrong-kind credential can repeatedly probe the operator endpoint without appearing in the supported signal.

Required repair: count every rejected `/metrics` authorization path exactly once, including correct-scope/non-wildcard and correct-scope/wrong-kind actors, without recording token, actor or repository material. Add API regressions for both post-authentication 403 branches and retain the existing 401/missing-scope cases.

### CR-005 — the metrics read is unbounded and can mix incompatible snapshots

`PostgresFactoryStore.metrics()` executes seven sequential aggregate statements over the complete durable `tasks`, `task_events`, `runs`, `capacity_allocations`, `usage_observations`, `kill_switches`, and `reconciliation_runs` histories (`factory/src/adaptive_factory/store.py:112-150`). Exact PostgreSQL `count(*)` and `sum(...)` over these append-preserved histories require work that grows with repository lifetime. This path has no `SET LOCAL statement_timeout`, no bounded page/window, and no fixed-row projection, despite the accepted requirement that store queries be bounded (`requirements.md:24-26`). Fixed JSON keys bound response cardinality; they do not bound database work.

The statements also run under the connection's ordinary `READ COMMITTED` behavior. Each statement may therefore observe a different committed snapshot: for example, a concurrent release between the run and allocation queries can return a live-lease value from before cleanup and an active-capacity value from after cleanup. That produces an apparent invariant violation even when the transaction that changed state was correct.

The 65-test verifier fixture proves values on a tiny quiescent database and caps only response bytes; it does not prove bounded query cost, timeout behavior, or cross-family consistency. Polling this endpoint as operational monitoring can consume progressively more database time and can emit internally inconsistent go/no-go evidence.

Required repair: source historical totals from transactionally maintained fixed-key counters and current gauges from bounded authoritative projections, and read the inventory in one coherent read-only snapshot/query. Apply an explicit bounded statement timeout. Add evidence with enlarged history and a concurrent state change proving bounded completion and invariant-consistent output.

### CR-006 — fence instrumentation can mask the stable stale-fence API contract

`FactoryService._fenced()` catches the authoritative `FenceError`, synchronously opens a second store operation through `record_fence_rejection()`, and only then executes the bare `raise` (`factory/src/adaptive_factory/service.py:85-91`). If the counter connection/update fails or blocks, that new exception or delay replaces the original stale-fence result. `record_fence_rejection()` has no statement/lock timeout and all rejected workers contend on one counter row (`factory/src/adaptive_factory/store.py:169-177`).

Consequently observability changes the behavior it observes: a heartbeat/release/budget request that should deterministically map to the documented 409 `stale_fence` can instead hang or surface an unrelated 500 when the metrics write is unavailable or contended. The new test proves only the successful counter-write case.

Required repair: preserve the original `FenceError` and its bounded API mapping regardless of metrics-path failure. Make the counter update bounded and define its failure behavior explicitly; then add store-fault/timeout tests proving stale requests still return `FenceError`/409 while a successful update remains durable.

## Controls confirmed

- All response family and outcome names are fixed in source; no caller-controlled label or identifier is projected. The response excludes task/source/actor IDs, request bodies, reasons, credentials and reasoning.
- Authentication counting uses a lock and saturates at signed-bigint maximum. Token comparison remains digest-based and constant-time across the configured set.
- Durable fence counting occurs only after an authorized worker mutation reaches store fencing; the failed worker transaction itself is rolled back before the separate counter transaction.
- The scanner repair changes only deterministic test-string construction plus its ledger entry. Runtime token values and the redaction assertion are unchanged, and the exact-head secret scan reports zero findings without a scanner suppression.
- Earlier intake authority, one-active-identity, lease/capacity fencing, accounting quarantine, retry/dead-letter, kill, audit and reconciliation code is unchanged from the previously reviewed recovery head except for the instrumentation wrapper described above.

## Verification evidence

- Initial `git status --short` was empty; `git rev-parse HEAD` and `HEAD^{tree}` returned the exact SHA/tree above.
- `git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1...fa043d48430963f82c52a76fbdabe2c35cd3d995` — PASS.
- Dependency-free contracts/state/migrations/service run — PASS, 24/24 in 0.013s.
- Independent real API reproduction — 403 for a valid reconcile-scoped/non-wildcard token followed by `auth_rejected: 0` for the authorized poll.
- Exact-head verifier receipt — PASS, 14/14: root 488/488, factory unit 24/24, fresh disposable PostgreSQL 65/65, actual restart/reconcile, source stability, architecture, contracts, SQL safety, secret scan, Ruff, Bandit and governance gates.

Concurrent route-selected review work changed other review reports after this review began. This reviewer changed only `code-review.md`; no product, contract, migration, test, architecture, governance, receipt, Git history or external state was modified. The report write changes the evidence-tree fingerprint, and the three Important findings require repair and a fresh exact-tree verifier/review wave before any PASS receipt or local-completion claim.
