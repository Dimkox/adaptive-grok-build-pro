# Independent test re-review — M4 durable factory control plane

## Verdict

**FAIL**

- Route: `b7f288f1e81e`
- Base SHA: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Prior reviewed HEAD: `cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06`
- Reviewed fix HEAD: `4230dc8e73bcf4dfcf6c60d294d379d44a30c698`
- Reviewed fix range: `cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06..4230dc8e73bcf4dfcf6c60d294d379d44a30c698`
- Reviewed full range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..4230dc8e73bcf4dfcf6c60d294d379d44a30c698`
- Exact-head verification fingerprint: `0092b4cd8152eb7919c94c610e66c7a4d71ad46382f1c5db852df41af0ac8789`

The prior TR-001 and TR-002 acceptance-test gaps are closed with direct, non-vacuous PostgreSQL assertions. One new Important authority TOCTOU remains: the test named transaction-bound proves revoke-before-validation rejection, but the database lock used after successful validation does not prevent a concurrent revocation from committing before the intake transaction commits. No Critical finding was found, but PASS is not justified while a revoked authority can race a successful intake.

## Finding

### TR-003 — Important — successful M0 validation is not fenced against concurrent revocation

Migration 009's authority functions select a valid observation or bootstrap exception using `FOR KEY SHARE` (`factory/src/adaptive_factory/resources/009_authority_audit_and_history_indexes.sql:32-59`). PostgreSQL key-share locking does not block an update of a non-key field such as `revoked_at`. Intake calls the function and then persists/supersedes work in the same transaction (`factory/src/adaptive_factory/store.py:254-369`), so another transaction can set `revoked_at` after the function returned `true` and before intake commits.

The current regression does not exercise that interleaving. It holds the source advisory lock, starts intake, commits the revocation while intake is still waiting, then releases the advisory lock and expects intake to fail (`factory/tests/test_postgres_integration.py:165-179`). This proves revoke-before-validation behavior, not revoke-after-successful-validation serialization.

An independent two-connection probe against the exact migration set on disposable PostgreSQL 17 produced:

```text
{'validator_returned': True, 'revocation_blocked_until_intake_commit': False}
```

Thus the authority row was successfully validated and remained updateable by a concurrent revoker before the validating transaction ended. The same lock mode is used for bootstrap exceptions.

Required closure:

- Use a row lock or atomic database operation that conflicts with `revoked_at` updates through the end of the intake transaction, for both observation and exception authority forms.
- Add a two-transaction regression that pauses intake after successful database validation, attempts revocation concurrently, and proves exactly one safe ordering: either revocation wins and intake fails, or intake commits before revocation can commit.
- Assert no accepted intent/task/supersession is persisted in the revocation-wins ordering. Do not satisfy the test solely by revoking before the validator runs.

## Prior blocker disposition

| Prior finding | Direct current evidence | Result |
| --- | --- | --- |
| Event budget exhaustion | A task with `max_events=2` consumes intake and claim events; release raises `BudgetError`, and the transaction rollback is asserted by exact state `leased`, unchanged `current_run_id`, and event count `2` (`factory/tests/test_postgres_integration.py:716-733`). | CLOSED |
| Repair cap exhaustion | A task with `semantic_repairs=1` is reconciled first to `retry`, then to `needs_human`; replay repairs zero and persisted `(repair_count, repair_limit)` remains `(1,1)` (`factory/tests/test_postgres_integration.py:735-753`). | CLOSED |
| Database deadline | An expired queued task cannot be claimed, and a live grant whose task deadline is expired rejects heartbeat with `FenceError` (`factory/tests/test_postgres_integration.py:755-770`). | CLOSED |
| Repository kill isolation | A valid `repository:repo/a` kill blocks repo A while repo B remains claimable and is cancelled cleanly (`factory/tests/test_postgres_integration.py:799-819`). | CLOSED |
| Reconciliation page and timeout | The disposable fixture creates 101 internally consistent expired runs, asserts page/replay/page results `(100,100,first,1,1)`, and uses a trigger to require the effective transaction setting to equal `5s`; no expired run remains (`factory/tests/test_postgres_integration.py:821-869`). | CLOSED |

## Additional fix-wave coverage

| Area | Non-vacuous assertion reviewed | Result |
| --- | --- | --- |
| Frozen authority and idempotency | Complete frozen intent changes in limits, producer head, or evidence digest change both intent digest and idempotency key; PostgreSQL exact replay deduplicates while changed limits/head supersede (`factory/tests/test_contracts.py:66-81`; `factory/tests/test_postgres_integration.py:97-124`). Command tests retain exact-result replay and changed-payload conflicts. | PASS, except TR-003 |
| Authority scope/policy/action | Cross-repository observation, wrong full-policy identity/check suffix, and wrong bootstrap action/scope fail; valid repository/policy/action-bound exception succeeds (`factory/tests/test_contracts.py:83-87`; `factory/tests/test_postgres_integration.py:126-163`). | PASS, except transaction serialization |
| Cross-attempt accounting | An unresolved full reservation forces `needs_human`, blocks retry claim, preserves reservation totals, sets `accounting_blocked`, and leaves one live reservation (`factory/tests/test_postgres_integration.py:772-797`). | PASS |
| Deadlock regression | Cancel and reconcile contend behind the same capacity lock; both finish without exception within bounded futures, and the task ends cancelled (`factory/tests/test_postgres_integration.py:871-900`). Production paths now acquire capacity before task/run locks. | PASS |
| History/query indexes | Real `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` plans over populated data must select named claim, audit, usage, active-reservation and reconciliation indexes (`factory/tests/test_postgres_integration.py:902-968`). Migration discovery requires versions 1-9 and the new index markers. | PASS |
| Audit semantics | Tampering task, run, or correlation identity independently makes v2 chain verification false (`factory/tests/test_postgres_integration.py:1047-1075`). Effective runtime DML denials and supported lifecycle remain direct. | PASS |
| Shipped bootstrap | The shipped admin path applies migrations, creates a bounded `NOINHERIT` login, validates readiness through the runtime DSN, and proves `session_user` differs from effective `factory_runtime` (`factory/tests/test_postgres_integration.py:970-987`). | PASS |
| Real Unix socket | Uvicorn is started on a prepared Unix listener; HTTPX over UDS receives `401` without credentials and the authenticated actor response with a bearer token (`factory/tests/test_server.py:20-56`). Absolute/no-follow credential ancestry negatives are also direct. | PASS |
| Closed API negatives | Malformed roles, repository shape, numeric type, cursor UUID, task UUID and reason shape/length all return bounded 4xx responses rather than 500 (`factory/tests/test_api.py:131-159`). | PASS |

## Concurrency and residual test quality

- The suite continues to prove a true two-worker/one-task claim race, monotonic replacement fence, late-holder rejection, exact 20/10/1 capacity limits, hidden-allocation fencing, retry/dead behavior, accounting replay, kill replay, and actual database restart.
- Capacity threshold filling remains sequential while one-task claim contention is concurrent. A barrier-based final-slot race remains useful Minor hardening, but the database-owned capacity functions and exact thresholds are exercised.
- The cancel/reconcile deadlock regression uses short scheduling delays to arrange contention. It exercises the shared lock path and is meaningful, though a database-side synchronization barrier would make the old lock-order failure more deterministic. This is Minor hardening, not the reason for FAIL.
- The disposable exit runner removes its exact container but still omits explicit anonymous-volume removal. This is local hygiene only.

## Exact-head verification evidence

The fingerprint-bound receipt created at `2026-09-01T20:26:54Z` records HEAD `4230dc8e73bcf4dfcf6c60d294d379d44a30c698`, fingerprint `0092b4cd8152eb7919c94c610e66c7a4d71ad46382f1c5db852df41af0ac8789`, and overall PASS:

```text
git-diff-check, change-spec, architecture, governance, secret-scan,
contract-structure, sql-safety, ruff, bandit, coverage, source-stability: PASS
python-unittest: 488 tests — OK
factory-unit: 24 tests — OK
factory-postgres-exit: 59 tests in 29.656s — OK
restart probe: one repair; replay no-op; higher fence; late holder rejected — PASS
```

`git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..4230dc8e73bcf4dfcf6c60d294d379d44a30c698` also produced no output. The verifier PASS establishes regression stability but cannot substitute for the uncovered authority interleaving demonstrated above.

The independent probe mutated only an exact disposable PostgreSQL container, which was removed. Its generated ignored `factory/.venv` was moved to the recoverable user trash at `/home/pall/.local/share/Trash/files/m4-review-venv.TfNybY/factory.venv`. No product, receipt, Git, shared database, Trust CI, external, or production state was changed by this review.
