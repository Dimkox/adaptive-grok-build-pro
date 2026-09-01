# Last exact-head independent test review — M4 durable factory control plane

## Verdict

**PASS**

- Route: `b7f288f1e81e`
- Base SHA: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Prior reviewed HEAD: `83e6b0d0c29e813932aa29b0d72ac4d85d27df7b`
- Reviewed product HEAD: `04261326e177e6d2014a576d3f4a0fb5feab56be`
- Focused recovery range: `83e6b0d0c29e813932aa29b0d72ac4d85d27df7b..04261326e177e6d2014a576d3f4a0fb5feab56be`
- Full reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..04261326e177e6d2014a576d3f4a0fb5feab56be`
- Exact-head verification fingerprint: `e7401c598db44069e77259d7e0f4da893e67b89f4778e195af540c3a753e86b0`

No Critical or Important test gap remains. The final recovery wave directly covers both legacy accounting projections omitted from migration 010 and readiness: a claimable schema-008 row blocked with zero aggregates, and a `ready_for_human` row retaining a live prior-attempt reservation. The test is seeded, state-bearing and fail-sensitive rather than a migration-version smoke test. All previously reviewed authority, cleanup, concurrency, capacity, fencing, retry, budget, kill, reconciliation, role, audit, query-plan, bootstrap, UDS and restart evidence remains green.

## Findings

No Critical or Important findings.

### Minor — capacity threshold filling remains sequential

The suite proves a real two-worker race for one task and exact global-reader 20/21, repository-reader 10/11 and writer 1/2 rejection boundaries, but fills the threshold cases sequentially. A barrier-based last-slot race remains useful hardening; it is not a blocker because the same database-owned allocation path is exercised concurrently and every exact threshold is asserted against PostgreSQL.

### Minor — deadlock test orchestration uses short delays

Cancel and reconcile are both held behind the same capacity lock and bounded futures prove completion without deadlock, but short sleeps arrange waiter order. A database-side synchronization barrier would make the historical lock-reversal failure more deterministic. The implementation and behavioral result both retain the required capacity-before-task ordering.

### Minor — exit cleanup does not explicitly remove anonymous volumes

The runner removes its unique disposable container in `finally` but omits explicit anonymous-volume removal. This is local test hygiene only.

## Schema-008 recovery coverage

The integration test creates a separate disposable database, creates the migration registry, applies exact migrations 001-008, records their checksums, and then seeds three distinct legacy projections before running the current migrator (`factory/tests/test_postgres_integration.py:984-1129`):

| Seeded schema-008 projection | Non-vacuous fixture evidence | Post-upgrade assertions | Result |
| --- | --- | --- | --- |
| Retry plus active full reservation | Failed run/attempt, live reservation, cost `25,000,000`, tokens `2,000,000`, wall `14,400`, and `accounting_blocked=false`. | State becomes `needs_human`; blocked flag is true; exact aggregates and one live reservation remain; claim returns no grant. | PASS |
| Retry blocked with zero aggregates | Separate accepted intent/task is `retry` with `accounting_blocked=true`, zero cost/token/wall and no reservation. | State becomes `needs_human`; exact tuple remains `(true,0,0,0,0)` rather than deleting or fabricating evidence. | PASS |
| Human-ready with prior live reservation | Separate `ready_for_human` task has a failed prior run with a live reservation `(500,600,700)`, plus a later completed run and usage observation; it begins unblocked. | State becomes `needs_human`; blocked flag is true; exact aggregates and the one live prior-run reservation are preserved. | PASS |

The combined assertion requires applied versions `[9,10,11]`, readiness `ready`, schema version `11`, accounting consistency true, and all three tasks in `needs_human` (`factory/tests/test_postgres_integration.py:1129-1145`). This tuple would fail if only migration metadata advanced or either legacy shape remained untouched.

The test additionally proves layered safety:

- the repository-wide claim returns no grant after quarantine;
- owner-only reintroduction of the active-reservation task as unblocked `retry` makes readiness `not_ready`, while the claim query independently still returns no grant;
- owner-only reintroduction of the live-reservation task as unblocked `ready_for_human` makes readiness `not_ready`;
- restoring that task to the explicit `needs_human/accounting_blocked` quarantine returns readiness to `ready`;
- a second migrator run returns an empty applied set (`factory/tests/test_postgres_integration.py:1146-1208`).

Forward migration 011 performs only evidence-preserving quarantine: blocked queued/retry tasks and unsafe `ready_for_human` tasks move to `needs_human/accounting_blocked`; no reservation or aggregate is released or rewritten (`factory/src/adaptive_factory/resources/011_legacy_accounting_quarantine.sql:1-16`). Current readiness explicitly includes queued, retry and ready-for-human unsafe accounting states, while claim separately requires zero aggregates, no live reservation and an unblocked task (`factory/src/adaptive_factory/store.py:66-95`, `:515-527`).

## Prior blocker closure retained

| Area | Direct evidence retained | Result |
| --- | --- | --- |
| M0 authority TOCTOU | Observation and exception are each tested for revoke-before-validation rejection with zero tasks and revoke-after-validation blocking through intake commit. Later reuse of each revoked authority fails. Migration 010 uses `FOR SHARE`. | PASS |
| Event/repair/deadline budgets | Exhausted ordinary-event release routes safely to human review; repair cap is persisted and not exceeded; expired queued and leased task deadlines reject claim/heartbeat. | PASS |
| Mandatory cleanup at event exhaustion | Release, expired-run reconcile and cancel each append exactly one mandatory event and one audit fact, release allocation/counters to exact zero, and replay without duplicate cleanup. | PASS |
| Cross-attempt accounting | A live prior-attempt reservation forces accounting recovery, retains exact totals/evidence and cannot retry. | PASS |
| Repository kill and bounded reconcile | Repository kill blocks its repository while another remains claimable. A 100+1 fixture proves paging/replay and a trigger requires effective `statement_timeout='5s'`. | PASS |
| Deadlock/fencing/capacity | Claim contention, monotonic replacement fence, late-holder rejection, hidden-allocation fencing, fixed cancel/reconcile lock order and exact 20/10/1 limits remain direct PostgreSQL tests. | PASS |
| Idempotency/auth negatives | Complete frozen intent defines duplicate identity; command replay returns exact durable results and changed commands conflict. Scope, repository, worker ownership, malformed closed commands and token ancestry fail closed. | PASS |
| Roles/audit/indexes | Effective-runtime forbidden DML raises `InsufficientPrivilege`; audit-v2 task/run/correlation tampering fails verification; populated `EXPLAIN ANALYZE` cases select named hot-path indexes. | PASS |
| Bootstrap/UDS/restart | Shipped bootstrap proves an effective runtime login. A real authenticated HTTP request crosses the Unix socket. PostgreSQL is actually restarted, reconciles once, replays zero, issues a higher fence and rejects the late holder. | PASS |

## Exact-head verification evidence

The inspected fingerprint-bound receipt was created at `2026-09-01T21:45:05Z` for exact HEAD `04261326e177e6d2014a576d3f4a0fb5feab56be` and fingerprint `e7401c598db44069e77259d7e0f4da893e67b89f4778e195af540c3a753e86b0`:

```text
14/14 verifier checks: PASS
python-unittest: 488 tests in 496.285s — OK
factory-unit: 24 tests in 0.013s — OK
factory-postgres-exit: 63 tests in 34.732s — OK
restart: one repair; replay no-op; higher fence; late holder rejected — PASS
source-stability: PASS
```

The durable ledger additionally records the focused schema-008 upgrade plus runtime-bootstrap PostgreSQL run at 2/2, migration/contract/state/service tests at 24/24, installer tests at 17/17, and the independent fresh exit/root runs on product commit `3bbafeb`. Migration discovery now requires contiguous versions 001-011 with 11 distinct checksums and installer inventory includes migration 011.

`git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..04261326e177e6d2014a576d3f4a0fb5feab56be` produced no output during this review.

This review changed only this report. It did not modify product code, receipts, Git, databases, external systems, production or Trust CI state. Writing the report changes the evidence-tree fingerprint; the coordinator must record the final route reviews and verification against the resulting one tree before AC-014/local closure.
