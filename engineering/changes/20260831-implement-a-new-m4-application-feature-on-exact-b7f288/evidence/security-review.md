# Final exact-head independent security review — M4 durable factory control plane

## Review binding and verdict

- Reviewer role: route-selected read-only `security_reviewer`
- Route: `b7f288f1e81e`
- Accepted M3 base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Prior reviewed HEAD: `daa3930cb84ba6547171583e41bcf0dee2ab1314`
- Exact reviewed product HEAD: `fa043d48430963f82c52a76fbdabe2c35cd3d995`
- Exact reviewed Git tree: `d8024cc0a188b4d58006a87fca5685e66471346a`
- Full reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..fa043d48430963f82c52a76fbdabe2c35cd3d995`
- Exact-head verifier: PASS, fingerprint `9ec2ce27d8dd0e0ee896573d282f4e0dcef2349a05914659d9bdac1e8dc37d75`

**FAIL**

- Critical findings: **0**
- Important findings: **1**
- Moderate findings: **1**

The authentication counter, fixed response inventory and redaction repair are locally bounded, but the newly security-relevant durable stale-fence metric is writable through an overbroad database role grant. That violates the M4 least-privilege and trustworthy-observability boundary and must be repaired before release closure.

## Important finding

### SR-005 — `factory_runtime` can forge or erase the durable stale-fence security signal

The metrics repair presents `factory_lease_reclaim_and_fence_rejection_total.fence_rejected` as a durable PostgreSQL-authoritative counter. `FactoryService._fenced()` catches a store `FenceError` after the failed transaction has unwound and calls `record_fence_rejection()`; that method performs a fixed-key, saturating `INSERT ... ON CONFLICT ... UPDATE` in a fresh transaction (`factory/src/adaptive_factory/service.py:85-149`; `factory/src/adaptive_factory/store.py:168-178`). The supported code path is safe and atomic.

The database authority beneath it is not capability-shaped. Migration 005 grants `factory_runtime` unrestricted `SELECT, INSERT, UPDATE` on the entire `factory.metric_counters` table (`factory/src/adaptive_factory/resources/005_security_accounting_commands.sql:31-36,71`). The table permits arbitrary unbounded text in both key columns and any nonnegative bigint value. No later migration revokes that grant, and the effective-role negative test does not probe `metric_counters` (`factory/tests/test_postgres_integration.py:1537-1581`).

Consequences under the repository's explicit compromised/effective-runtime-role threat boundary:

- the runtime credential can set the allow-listed `fence_rejected` value to zero or any chosen number, so an operator cannot trust the signal to reveal stale-holder attacks or fencing defects;
- it can insert arbitrary metric names/outcomes and update them without going through the fixed allow-listed increment path;
- because those key columns have no length bound, direct runtime access can create unbounded metric-key storage even though the HTTP response itself has fixed cardinality.

The HTTP API exposes no raw SQL, so this is not an unauthenticated remote injection. It is nevertheless Important: M4 repeatedly treats the effective runtime role as an independently constrained security boundary, and earlier capacity/allocation findings were repaired by removing direct DML and exposing only capability-shaped functions. A security rejection counter controlled by the same broad runtime authority is not durable security evidence.

Required repair: add a forward migration that revokes direct `INSERT/UPDATE` (and preferably table-wide `SELECT` if not needed) on `metric_counters` from `factory_runtime`; expose a fixed-search-path, PUBLIC-revoked, narrowly granted security-definer increment function that accepts no caller-selected metric/outcome/value or validates an explicit closed allow-list and can only saturating-increment. Use that capability from `record_fence_rejection()`. Add effective-role tests proving arbitrary insert, reset/decrement and unknown-key writes fail while concurrent supported increments remain monotonic and the operator metrics response still reports the exact value. Do not edit an applied migration.

## Moderate finding

### SR-006 — authenticated metric collection has unbounded historical scan cost

`PostgresFactoryStore.metrics()` performs full aggregate counts/sums over durable tasks, task events, runs, observations and reconciliation history without a statement timeout (`factory/src/adaptive_factory/store.py:112-165`). Output cardinality and response size are fixed, but query work grows with retained history. A wildcard operator over the protected UDS is already highly privileged, so this is not an Important cross-tenant or unauthenticated DoS. It is a real local availability risk if metrics are scraped frequently after long retention.

Recommended hardening: set a bounded read-only transaction timeout for metrics and either maintain capability-shaped counters or document/test a bounded scrape interval and query-plan/retention envelope. A timeout should return a bounded unavailable response without affecting control-plane transactions.

## Metrics authentication and disclosure assessment

- `Authenticator` hashes configured credentials once and compares every candidate digest against every configured digest using `hmac.compare_digest`; valid and invalid bearer candidates traverse the full actor tuple. The new rejection counter does not change token matching or short-circuit on actor identity.
- Missing/malformed bearer, unmatched bearer and missing-scope requests increment a lock-protected saturating signed-64-bit process counter before returning bounded 401/403 responses. Increment/read operations are serialized, so concurrent requests cannot lose Python-side increments. The counter intentionally resets on server restart and is documented as process-local rather than durable evidence.
- `/metrics` still requires the `factory:reconcile` scope at the authentication boundary and then requires operator kind plus wildcard repository authority at the service boundary. A repository-scoped actor cannot read global operational aggregates.
- The response contains only three fixed families and fixed aggregate keys. It has no actor ID, repository/source/task/run ID, body, reason, token, prompt or other variable label. Tests require the response to omit the valid fixture credentials and source identity and remain at most 2 KiB.
- Missing, invalid and scope-denied auth paths are directly tested as 401/401/403 followed by `auth_rejected=3`; a real UDS request separately proves missing auth produces `auth_rejected=1`. Uvicorn access logging remains disabled, so no bearer value is copied into standard access logs.
- Commit `fa043d4` only constructs deterministic test credentials from string fragments to satisfy the conservative scanner. Runtime credential bytes and negative disclosure assertions are unchanged; the exact verifier reports zero potential secrets, with no scanner suppression or rule weakening.

## Prior security closures reconfirmed

- **Authority/TOCTOU:** observation and exception validators retain static schema-qualified SQL, fixed search paths, PUBLIC-revoked EXECUTE and `FOR SHARE` serialization against revocation. Both pre-validation rejection and post-validation blocking interleavings remain tested.
- **Schema-008 recovery:** the same-identity generation-1/generation-2 regression proves migration 011 avoids the active-identity collision, retains accounting evidence in `superseded/accounting_blocked`, preserves generation 2 as the exact claim target, fails readiness when the quarantine marker is removed and replays empty.
- **Repository and worker isolation:** global metrics/reconciliation/kill require wildcard operator authority; task resources remain repository checked; worker grants bind actor, task/run, repository, owner, fence, packet, allocation, lease/deadline and budget.
- **Capacity/accounting/cleanup:** direct capacity/allocation authority remains revoked or capability-shaped; claim and completion fail closed on accounting; mandatory release/reconcile/cancel cleanup is idempotent and audited even after ordinary-event exhaustion.
- **Audit and credentials:** audit-v2 binds task/run/correlation and remains append-only under runtime; actor/token files retain absolute no-follow owner/mode checks; errors and metrics remain redacted.
- **Transport/external boundary:** the server binds only an owned mode-0660 Unix socket with a protected parent. No TCP, provider/shell/repository/Git/GitHub/systemd/deployment/production or Trust CI mutation path was introduced.

## Exact verification evidence

The inspected receipt was created at `2026-09-01T22:57:57Z` for exact HEAD `fa043d48430963f82c52a76fbdabe2c35cd3d995` and fingerprint `9ec2ce27d8dd0e0ee896573d282f4e0dcef2349a05914659d9bdac1e8dc37d75`:

```text
14/14 verifier checks: PASS
secret-scan: 0 potential secrets — PASS
Bandit and Ruff — PASS
root python-unittest: 488 tests in 485.320s — OK
factory-unit: 24 tests in 0.013s — OK
factory-postgres-exit: 65 tests in 35.876s — OK
actual restart: one repair; replay no-op; higher fence; late holder rejected — PASS
source-stability: PASS
```

`git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..fa043d48430963f82c52a76fbdabe2c35cd3d995` produced no output. `git rev-parse HEAD` and `HEAD^{tree}` matched the exact SHA/tree above. Before this report write, the only worktree change was the concurrently produced final `test-review.md`; it was not modified by this reviewer.

This review changed only `security-review.md`. It did not modify product code, receipts, Git history, databases, credentials, external systems, production or Trust CI state. This FAIL is local review evidence, not authority for migration, PR delivery, merge, release or deployment.
