# Final exact-head independent security review — M4 durable factory control plane

## Review binding and verdict

- Reviewer role: route-selected read-only `security_reviewer`
- Route: `b7f288f1e81e`
- Accepted M3 base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Exact reviewed clean evidence HEAD: `9fe779ab9f90719201acfd01160d3452658ff075`
- Exact reviewed evidence tree: `05707b35fb10ab9a29d3be35478faf4ef84789a1`
- Exact reviewed product commit: `4f75558770f2f332b32b4a47fe6afa61fcc524ec`
- Exact reviewed product tree: `5e4a46bab94f4943b6fc698472e309d4ee24fab2`
- Full reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..9fe779ab9f90719201acfd01160d3452658ff075`
- Exact-head verifier: PASS, fingerprint `2b9b3ee786663e3adba2e2f85e51e7c752c8e57166a0d7af6e3f62a88f4b45e8`

**PASS**

- Critical findings: **0**
- Important findings: **0**
- Moderate findings: **0**

No security finding at Moderate severity or above remains on the exact reviewed tree. Prior SR-005 and SR-006 are closed by forward migration `012`; the final `4f75558` repair preserves the authoritative fence error, makes best-effort instrumentation handling explicit and changes no runtime authority.

## Final fix assessment

### Migration 012 privilege and capability boundary — closed

- Migration `012` takes write-conflicting locks over every authoritative snapshot source before backfill, renames the former generic counter table as explicitly untrusted evidence, and revokes all runtime/PUBLIC access to it (`factory/src/adaptive_factory/resources/012_bounded_metrics_snapshot.sql:1-7`). Forged pre-012 values are not imported; the trusted fence epoch starts at zero.
- The replacement counter is a fixed 21-value singleton with closed nonnegative columns, not caller-selected metric/outcome keys (`012_bounded_metrics_snapshot.sql:9-32`). Runtime has no `SELECT`, `INSERT`, `UPDATE` or `DELETE` on the singleton or kill-switch head table (`012_bounded_metrics_snapshot.sql:258-261`).
- Runtime receives only `read_metrics_snapshot()` and the no-argument `increment_fence_rejected()` capability. The latter can only monotonically increment the one fence value and saturates at signed-bigint maximum (`012_bounded_metrics_snapshot.sql:231-256,262-273`). PUBLIC execute and runtime execution of internal trigger functions are denied.
- Every security-definer function fixes `search_path=pg_catalog,factory`; relations are schema-qualified. The trigger functions are migration-owner maintained and are executable as triggers without granting runtime generic function or table authority (`012_bounded_metrics_snapshot.sql:74-229`). No caller-controlled dynamic SQL or search-path substitution exists.
- Effective-role PostgreSQL coverage proves both counter tables unreadable/unwritable by runtime, internal trigger functions uncallable, supported concurrent increments exact and monotonic, saturation bounded, and unknown/reset/decrement writes denied (`factory/tests/test_postgres_integration.py:955-1012`). The schema-008 upgrade case retains forged legacy rows only as inaccessible evidence and initializes the new snapshot from authoritative tables (`factory/tests/test_postgres_integration.py:1455-1510`).

### Authentication accounting and disclosure — closed

- `Authenticator` stores only SHA-256 token digests, compares the candidate against every configured digest with `hmac.compare_digest`, and never emits a token, actor or repository value (`factory/src/adaptive_factory/api.py:39-68`). Uvicorn access logging remains disabled (`factory/src/adaptive_factory/server.py:96-103`).
- The HTTP middleware increments one lock-protected saturating process counter after every final application 401/403, covering missing/malformed credentials, unmatched bearer, missing scope, actor-kind, repository and trusted-authority denials without changing endpoint error precedence (`factory/src/adaptive_factory/api.py:182-203`). It has no labels or reset API and intentionally resets only with the process.
- The exact actor matrix proves 401/401/403/403/403 produces `auth_rejected=5`, a fresh application starts at zero, output stays at or below 2 KiB, and no credential/actor/repository material appears (`factory/tests/test_api.py:140-196`). A real UDS request independently proves one missing-auth rejection (`factory/tests/test_server.py:20-65`).
- `/metrics` still requires `factory:reconcile` at authentication and wildcard operator authority at the service boundary; a repository-scoped operator or wrong actor kind receives 403 and cannot read global state (`factory/src/adaptive_factory/api.py:219-226`; `factory/src/adaptive_factory/service.py:172-189`).

### Bounds, denial of service and fence precedence — closed

- Store metrics now execute one constant-row snapshot read rather than historical scans, with transaction-local 5-second statement and 500-millisecond lock timeouts; errors map to a bounded 503 (`factory/src/adaptive_factory/store.py:117-149`; `factory/src/adaptive_factory/api.py:178-180`). PostgreSQL coverage proves one data statement, atomic pre/post-release values, a one-row plan and bounded failure under an exclusive counter lock (`factory/tests/test_postgres_integration.py:1014-1097`).
- Fence accounting uses a one-second connection timeout, 100-millisecond lock timeout and 250-millisecond statement timeout (`factory/src/adaptive_factory/store.py:151-155`). `FactoryService._fenced()` records only after the authoritative operation has raised `FenceError`, catches instrumentation failure, and bare re-raises the identical error (`factory/src/adaptive_factory/service.py:85-97`). A locked counter therefore cannot delay beyond the bound or replace exact `409 stale_fence`; the next unlocked rejection increments normally (`factory/tests/test_postgres_integration.py:1099-1167`; `factory/tests/test_service.py:48-70`).
- Request bodies remain cumulatively limited to 1 MiB even without a usable Content-Length; malformed length is bounded 400 and oversized declared/streamed bodies are 413 (`factory/src/adaptive_factory/api.py:182-200`; `factory/tests/test_api.py:109-130`). Pages, repository lists, lease duration, reconciliation candidates/time and audit verification remain explicitly bounded.
- The fixed snapshot row adds intentional write serialization but not an authority or unbounded-work path. The reproduced reconciliation/cancel inversion was repaired by making the reconciliation trigger a no-op until a completed-state delta exists; supported state changes retain the established capacity-before-task/counter order and the real deadlock regression passes.

## Full prior-closure reconfirmation

- **M0 authority and TOCTOU:** persisted observations/exceptions are repository, full-policy, action, issuer/scope/expiry and exact-head bound. Fixed-search-path definer validators hold `FOR SHARE`, which conflicts with revocation updates through intake commit. Both pre-validation rejection and post-validation blocking interleavings remain covered.
- **Actor/resource authorization:** server-side checks bind scope, actor kind, repository, task/run owner, packet digest, fence, live allocation, lease/deadline and budget. Global reconcile/metrics and global kill require wildcard operator authority; repository actors cannot cross tenant boundaries.
- **Capacity, accounting and cleanup:** runtime cannot forge capacity counters or allocations and cannot release allocations directly; only closed database capabilities remain. Claim and completion fail closed on accounting. Cancel, supersession, release and reconciliation clean runs/attempts/allocations idempotently and preserve mandatory event/audit evidence after ordinary-event exhaustion.
- **Migration recovery:** schema-008 unsafe accounting is quarantined without losing task/run/reservation/usage/audit evidence. The newer active generation remains the exact claim target; readiness fails if the explicit quarantine marker is removed. Migration `012` is forward-only and a lock/timeout failure atomically leaves schema 011 intact.
- **Audit and secrets:** audit-v2 binds task, run, correlation, actor, action, resource, reason, timestamp and canonical metadata; runtime cannot update/delete the append-only log. Actor/token files require absolute owner-pinned no-follow `0600` paths through trusted ancestry. Bounded application errors do not expose SQL, bearer values or configuration secrets.
- **Transport and external authority:** the server pre-binds only an owned mode-0660 Unix socket beneath an owned non-writable parent; there is no TCP listener, provider/repository command, shell, Git/GitHub, connector, systemd, deployment, production mutation or Trust CI publication path in `factory/src`.
- **M4 to M9 documentation:** every handoff is explicitly digest/SHA-bound and invalidated by predecessor, policy, artifact or evidence change. M5/M6 are provisional and must restack in dependency order; M7-M9 are roadmap-only. The documents grant no intake-policy, cross-task, signing-key, Trust CI, merge, production or human-approval authority, retain the current L2 cap and human-owned production promotion, and state that the deadline waives no gate.

## Exact verification and reviewer evidence

The inspected verifier receipt was created at `2026-09-02T00:13:05Z` for exact HEAD `9fe779ab9f90719201acfd01160d3452658ff075` and fingerprint `2b9b3ee786663e3adba2e2f85e51e7c752c8e57166a0d7af6e3f62a88f4b45e8`:

```text
14/14 verifier checks: PASS
secret-scan: 0 potential secrets — PASS
Bandit and Ruff — PASS
root python-unittest: 488 tests in 496.646s — OK
factory-unit: 24 tests — OK
factory-postgres-exit: 70 tests in 41.360s — OK
actual restart: one repair; replay no-op; higher fence; late holder rejected — PASS
source-stability: PASS
```

This reviewer additionally ran the focused service/migration suite: 13/13 in 0.010s, including identical fence-error precedence, wildcard global authorization, M0 rejection, runtime boundaries, migration-012 markers and final-PID1 readiness. `git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..9fe779ab9f90719201acfd01160d3452658ff075` produced no output. The worktree was clean immediately before this report write.

This review changed only `security-review.md`. It did not modify product code, receipts, Git history, databases, credentials, external systems, production or Trust CI state. This PASS is local exact-tree review evidence only; it cannot authorize migration rollout, PR delivery, merge, release or deployment, and any later product/tree change requires fresh exact-SHA verification and affected independent reviews.
