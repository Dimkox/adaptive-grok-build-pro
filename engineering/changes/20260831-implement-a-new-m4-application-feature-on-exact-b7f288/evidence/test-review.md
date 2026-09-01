# Independent test review — M4 durable factory control plane

## Verdict

**FAIL**

- Route: `b7f288f1e81e`
- Base SHA: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Reviewed product HEAD: `cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06`
- Reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06`
- Exact-product verification fingerprint inspected: `13363f4e7d5b058ae864ca54c165bb671e6355c2d7082f60c023a01154347df3`

No Critical finding was found, but Important acceptance-test gaps remain. The current suite is strong and the exact product head passes the full verifier, including a fresh disposable PostgreSQL 17 run and actual restart. It does not, however, directly exercise every mandatory fail-closed budget, repository-kill, and bounded-reconciliation behavior claimed by AC-007 through AC-009 and AC-012. PASS is therefore not justified under the route's test-plan standard.

## Findings

### TR-001 — Important — event/repair/deadline limits are not behaviorally exercised

AC-007 requires the 14,400-second deadline and cost, token, output, event, and repair ceilings to fail closed; AC-012 requires real PostgreSQL evidence for budgets. The integration suite directly proves cost/token/wall reservation settlement and overflow (`factory/tests/test_postgres_integration.py:118-175`, `:473-597`), plus output observation deduplication and overflow. It never drives the event ceiling to rejection, never exhausts a task's persisted `repair_limit`, and never proves an expired task deadline cannot be claimed.

The only test reference to the repair ceiling is a string-presence assertion for `repair_limit` in packaged SQL (`factory/tests/test_migrations.py:31-52`). `max_events` and `semantic_repairs` otherwise appear only in valid fixture payloads. The restart probe repairs exactly one lease (`factory/tests/postgres_restart_probe.py:85-96`), so it cannot establish cap behavior. Production branches at `factory/src/adaptive_factory/store.py:159-183` and `:941-953` are consequently unexecuted at their rejection boundaries.

Required closure: add disposable-PostgreSQL tests with deliberately small limits that (1) consume the final event and reject the next state mutation without partial persistence, (2) exhaust semantic repairs and prove no repair beyond the persisted ceiling, and (3) expire the database-time task deadline and prove claim/mutation rejection. Assertions must include task/run/event/counter state after failure, not only exception type.

### TR-002 — Important — repository kill and reconciliation bounds lack direct acceptance evidence

AC-008 says both global and repository kill switches block new claims. The real PostgreSQL test enables only `scope_key="global"` and asserts a claim returns `None` (`factory/tests/test_postgres_integration.py:599-612`). Repository-kill coverage is limited to authorization rejection against a recording fake (`factory/tests/test_service.py:102-134`); no test proves a valid repository kill blocks that repository while leaving another repository claimable.

AC-009 requires reconciliation to process at most 100 candidates within a five-second database bound. Existing tests cover one/two candidates, exact replay, orphan isolation, and counter inconsistency (`factory/tests/test_postgres_integration.py:407-426`, `:672-716`), but none creates more than 100 expired candidates or asserts a 100-item page/cursor boundary. The five-second guarantee is present only as implementation SQL (`SET LOCAL statement_timeout='5s'` at `factory/src/adaptive_factory/store.py:918`) and is not asserted by a test.

Required closure: add real PostgreSQL cases for repository-scoped kill isolation and for more than 100 expired candidates, asserting first-page count/cursor, remaining live work, replay/idempotency, and subsequent bounded completion. Assert the transaction's effective `statement_timeout` or deterministically provoke a bounded timeout so the five-second contract is test-bearing.

### Minor — capacity threshold filling remains sequential

The suite proves a genuine two-worker race for one task (`factory/tests/test_postgres_integration.py:369-405`) and exact 20/10/1 capacity thresholds (`:428-471`), but the threshold fill itself is sequential. A barrier-based last-slot race would strengthen proof that database-owned counters cannot oversubscribe under simultaneous claims. This is not separately Important because concurrency and each exact capacity boundary are already exercised against PostgreSQL.

### Minor — API and Unix-socket behavior are not joined by an end-to-end UDS request

Socket ownership/mode tests, API/auth tests, and PostgreSQL-backed API mutations exist, but no automated case starts the server and sends an authenticated request over the actual Unix socket. This is useful rollout hardening; the missing core acceptance evidence is already captured in TR-001/TR-002.

## Coverage that is direct and non-vacuous

| Area | Evidence reviewed | Result |
| --- | --- | --- |
| Immutable intake and supersession | Closed contract negatives reject unknown fields, unsupported versions, dirty SHA, handoff mismatch, duplicate acceptance IDs and stale M0 (`factory/tests/test_contracts.py:57-104`). PostgreSQL duplicate replay returns the same task and changed source creates a replacement while superseding the old task (`factory/tests/test_postgres_integration.py:66-77`). | PASS |
| Claim concurrency and fencing | Two threads compete for one task and exactly one receives a grant; an expired run is reconciled, the replacement fence is greater, and the old heartbeat raises `FenceError` (`factory/tests/test_postgres_integration.py:369-405`). Hidden allocation corruption separately fences heartbeat, release, reservation and usage and makes reconcile fail closed (`:672-716`). | PASS |
| Capacity | Real PostgreSQL assertions establish 20 global readers, 10 readers for `repo/a`, and one writer, with the next claim returning `None` (`factory/tests/test_postgres_integration.py:428-471`). | PASS, with Minor concurrency hardening |
| Retry/dead semantics | State-policy tests enumerate the closed retryable failure set and stop attempt three; PostgreSQL performs three worker-lost attempts and asserts `dead` (`factory/tests/test_state.py:49-62`; `factory/tests/test_postgres_integration.py:473-485`). | PASS |
| Idempotency/correlation | API-backed PostgreSQL cases assert exact response replay, changed-payload `409`, durable empty-claim replay, reservation replay before stale-fence validation, usage dedupe/conflict, kill replay, and stored correlation IDs (`factory/tests/test_postgres_integration.py:211-367`). | PASS |
| Authentication/authorization | Missing bearer/idempotency/correlation are rejected; token symlink/mode checks are direct; service tests reject missing scope, cross-repository intake, cross-worker grants, and unauthorized kill scopes before store calls (`factory/tests/test_api.py:73-134`; `factory/tests/test_service.py:40-134`). | PASS for tested boundaries |
| Effective PostgreSQL roles | The suite checks role flags and privileges, then executes forbidden intent/event/audit/capacity/allocation DML under `SET LOCAL ROLE factory_runtime` and requires `InsufficientPrivilege`; a supported lifecycle still succeeds (`factory/tests/test_postgres_integration.py:614-670`). This is effective-role behavior, not metadata-only evidence. | PASS |
| Actual restart/reconciliation | The probe invokes `docker restart`, reconnects with a fresh service/store, asserts repairs `1` then `0`, receives a higher fence, and rejects the late holder (`factory/tests/postgres_restart_probe.py:68-97`). | PASS |
| No execution/external surface | OpenAPI negatives assert the forbidden provider, shell, Git, PR, deploy and systemd endpoints are absent; architecture/root verification also passed. | PASS for declared surface |

## Verifier capability matrix

The `factory-postgres-exit` gate is included only for PR/release modes when the runner exists. It skips only when `GROK_VERIFY_CAPABILITY` exactly equals `repository-sandbox`; otherwise it executes the exit runner and propagates failure (`.grok-stack/adaptive_grok/verification.py:590-608`). The four focused tests are non-vacuous:

- unset capability plus a successful synthetic runner => `pass`;
- exact `repository-sandbox` plus `SystemExit(9)` => named `skip` with the capability reason;
- unset capability plus `SystemExit(9)` => `fail`;
- `repository-sandbox-extra` plus `SystemExit(9)` => `fail`.

Commit `cf0219b` explicitly removes an inherited capability value in both local pass/fail tests, closing the branch-history/environment-dependent false-skip defect. A caller-controlled environment variable is not merge authority, so local completion must still require an exact-head receipt whose `factory-postgres-exit` is `pass`, not `skip`. The inspected receipt satisfies that condition for product HEAD `cf0219b`.

## Verification performed

```text
git rev-parse HEAD
  cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06

git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06
  PASS (no output)

focused verifier capability tests
  4 tests in 8.654s — OK

dependency-free factory contracts/state/migrations/service
  21 tests in 0.012s — OK

python3 factory/tests/run_disposable_exit.py
  43 tests in 17.295s — OK
  PASS: PostgreSQL restarted; one repair; replay no-op; higher fence; late holder rejected
  PASS: disposable PostgreSQL + API + effective roles + actual restart/reconciliation

exact-product verification receipt (created 2026-09-01T14:59:00Z)
  status=pass
  product head=cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06
  tree_fingerprint=13363f4e7d5b058ae864ca54c165bb671e6355c2d7082f60c023a01154347df3
  python-unittest=pass; factory-unit=pass; factory-postgres-exit=pass; source-stability=pass
```

The verification receipt predates the independent review-report rewrites and therefore does not bind the final evidence tree. After TR-001 and TR-002 are remediated and independently rereviewed, final verification and all route-selected reviews must be recorded against one new fingerprint for AC-014. No product, receipt, Git, external, production, or Trust CI state was changed by this review.
