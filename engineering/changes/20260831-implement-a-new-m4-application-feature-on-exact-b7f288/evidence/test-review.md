# Final exact-head independent test review — M4 durable factory control plane

## Verdict

**PASS**

- Reviewer role: route-selected read-only `test_reviewer`
- Route: `b7f288f1e81e`
- Accepted M3 base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Prior reviewed HEAD: `daa3930cb84ba6547171583e41bcf0dee2ab1314`
- Exact reviewed product HEAD: `fa043d48430963f82c52a76fbdabe2c35cd3d995`
- Exact reviewed Git tree: `d8024cc0a188b4d58006a87fca5685e66471346a`
- Full reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..fa043d48430963f82c52a76fbdabe2c35cd3d995`
- Exact-head verifier fingerprint: `9ec2ce27d8dd0e0ee896573d282f4e0dcef2349a05914659d9bdac1e8dc37d75`

No Critical or Important test/evidence gap remains. The RR-003 observability repair has direct, state-changing PostgreSQL coverage for the fixed operational inventory, separate API coverage for missing/invalid/scope-denied authentication failures, a real UDS assertion, credential/redaction bounds, and exact-head secret-scan plus full verifier evidence. All previously reviewed schema migration, accounting recovery, authority, cleanup, concurrency, capacity, fencing, idempotency, role, audit, bootstrap and restart coverage remains present in the expanded 65-test disposable PostgreSQL exit.

## Findings

No Critical or Important findings.

## Operational metrics inventory coverage

`test_release_metrics_inventory_tracks_durable_operations_and_rejections` is a non-vacuous real PostgreSQL test (`factory/tests/test_postgres_integration.py:853-952`). It drives five independent task histories rather than inserting expected metric rows directly:

- one task stays queued;
- one task takes three closed-infrastructure failures and becomes dead, exercising retry and dead projections;
- one live task reserves exact cost/token/wall values `(7,11,13)`;
- another live task records exact observed cost/token/output values `(5,6,7)`;
- another lease is expired in PostgreSQL and reconciled, producing one candidate, one repair and one reclaimed run;
- a stale heartbeat using the repaired grant raises `FenceError`, exercising the separately committed durable fence-rejection counter;
- a global kill is enabled through the supported service path;
- one missing-auth request exercises the process-local rejection total.

The authorized response then asserts all three and only the three contract families, exact fixed key sets, and behaviorally derived values:

```text
accepted/queued/retry/dead = 5/1/1/1
transition_events >= 15
live_leases/reclaimed/fence_rejected = 2/1/1
active_capacity = 2
reserved cost/tokens/wall = 7/11/13
observed cost/tokens/output = 5/6/7
active_kills = 1
reconciliation runs/candidates/repaired = 1/1/1
auth_rejected = 1
```

The test also requires the response to exclude both the credential and a source identity and remain at most 2 KiB. Exact key-set assertions prevent an unbounded label or accidental payload expansion from passing unnoticed. Existing accounting and supersession tests continue to exercise the durable sources behind the two pre-existing `accounting_blocked` and `superseded` projections.

## Authentication rejection and fixture integrity

`test_metrics_counts_auth_rejections_without_exposing_credentials` independently creates two actors and sends three distinct rejected requests (`factory/tests/test_api.py:139-162`):

1. missing authorization header -> 401;
2. invalid bearer credential -> 401;
3. valid credential without the required scope -> 403.

The next valid wildcard-operator request must return `auth_rejected=3`; neither valid fixture credential may appear in the response, whose body is bounded to 2 KiB. This proves counting occurs at the authentication boundary even though Uvicorn access logging remains disabled. `test_authenticated_request_reaches_real_unix_socket` separately sends a missing-auth request through an actual Unix socket and requires the subsequent authenticated response to report `auth_rejected=1`.

Commit `fa043d4` changes only deterministic test credential construction from one literal to concatenated fragments. The resulting runtime strings and all auth/redaction assertions are unchanged. The exact-head secret-scan gate reports `0 potential secrets`; no scanner rule, exclusion or production authentication behavior was weakened. The focused ledger also records the repaired API auth test at 1/1 and a post-repair fresh PostgreSQL exit at 65/65 plus restart.

## Prior blocker coverage retained

| Area | Direct evidence retained | Result |
| --- | --- | --- |
| Schema-008 upgrade | Real non-empty 008-to-current migration applies exactly 009-011, handles blocked-zero and live-reservation projections, preserves same-identity gen1 evidence, leaves gen2 uniquely claimable, verifies readiness fault injection and empty replay. | PASS |
| Authority/TOCTOU | Observation and exception paths cover revoke-before rejection and revoke-after serialization through intake commit. | PASS |
| Cleanup/bounds | Event, repair and database-deadline exhaustion fail closed; release, reconcile and cancel perform mandatory cleanup exactly once at exhausted ordinary-event budget. | PASS |
| Accounting/idempotency | Cross-attempt reservations force recovery; replay remains exact; completion requires settled accounting; changed commands conflict. | PASS |
| Concurrency/fencing/capacity | Real two-worker contention, monotonic fences, late-holder/hidden-allocation rejection, fixed cancel/reconcile lock order and exact 20/10/1 ceilings remain covered. | PASS |
| Kill/reconciliation/indexes | Repository kill isolation, 100+1 paging, exact `5s` transaction bound, two-pass restart reconciliation and populated named-index plans remain direct PostgreSQL assertions. | PASS |
| Roles/bootstrap/UDS | Effective-role forbidden DML, isolated schema, shipped owner/runtime bootstrap, authenticated UDS request and absence of TCP/execution endpoints remain covered. | PASS |

## Exact-head verification evidence

The inspected fingerprint-bound receipt was created at `2026-09-01T22:57:57Z` for exact HEAD `fa043d48430963f82c52a76fbdabe2c35cd3d995` and tree fingerprint `9ec2ce27d8dd0e0ee896573d282f4e0dcef2349a05914659d9bdac1e8dc37d75`:

```text
14/14 verifier checks: PASS
secret-scan: 0 potential secrets — PASS
python-unittest: 488 tests in 485.320s — OK
factory-unit: 24 tests in 0.013s — OK
factory-postgres-exit: 65 tests in 35.876s — OK
restart: one repair; replay no-op; higher fence; late holder rejected — PASS
source-stability: PASS
```

The ledger additionally records RED failures for missing auth inventory and absent PostgreSQL operational keys; focused GREEN at API 1/1, PostgreSQL 1/1 twice, API/server/service 21/21 and Ruff; the first verifier's isolated secret-scan failure; and the scanner-safe repair followed by focused 1/1, PostgreSQL 65/65 plus restart, then the exact final 14/14 verifier above.

`git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..fa043d48430963f82c52a76fbdabe2c35cd3d995` produced no output. Before this report write, `git rev-parse HEAD` and `HEAD^{tree}` matched the exact SHA/tree above and `git status --short` was empty.

This review changed only `test-review.md`. It did not modify product code, receipts, Git history, databases, external systems, production or Trust CI state. Writing the report changes the evidence-tree fingerprint; the coordinator must bind final review/verification receipts to the resulting final tree before claiming local closure.
