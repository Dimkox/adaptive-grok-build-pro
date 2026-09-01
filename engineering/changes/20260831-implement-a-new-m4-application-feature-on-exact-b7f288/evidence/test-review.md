# Final exact-head independent test review — M4 durable factory control plane

## Verdict

**PASS**

- Route: `b7f288f1e81e`
- Accepted M3 base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Prior reviewed HEAD: `04261326e177e6d2014a576d3f4a0fb5feab56be`
- Reviewed product HEAD: `daa3930cb84ba6547171583e41bcf0dee2ab1314`
- Active-generation fix commit: `d15302f0bf5250cb4c7a3d623ccd56c96acdb16e`
- Full reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..daa3930cb84ba6547171583e41bcf0dee2ab1314`
- Exact-head verifier fingerprint: `ad41a13355b097f4be0a3d6c3754b9cc4de8178824e801ac264fad81c852e794`

No Critical or Important test/evidence gap remains. The final regression directly reproduces the schema-008 same-identity generation-1/generation-2 collision that failed before the repair, proves atomic migration through 011, preserves the unsafe generation-1 accounting evidence under an explicit non-active quarantine, and proves generation 2 remains the unique claim target. Previously reviewed M4 behavioral coverage remains present in the exact-head 63-test disposable PostgreSQL suite and the exact-head verifier is fully green.

## Findings

No Critical or Important findings.

## Same-identity schema-008 RED/GREEN regression

`factory/tests/test_postgres_integration.py:984-1237` creates a separately named disposable database, builds the schema and checksum registry through exact migration 008, seeds durable legacy data, then applies the packaged migrator.

The decisive fixture is non-vacuous:

- generation 1 and generation 2 use the same repository, source type and source ID (`legacy-ready-reservation`);
- generation 1 begins `ready_for_human` with aggregates `(500,600,700)`, a failed prior run, an unreleased reservation, a later completed run and a usage observation;
- generation 2 begins `queued`, unblocked and otherwise eligible for claim;
- the ledger records the pre-fix RED as a real PostgreSQL `UniqueViolation` on `tasks_one_active_identity` while migration 011 tried to make generation 1 index-active.

The GREEN assertions are exact and fail-sensitive:

- migrations applied are exactly `[9,10,11]`, readiness is `ready`, schema version is 11 and accounting consistency is true;
- generation 1 becomes `superseded/accounting_blocked`, while generation 2 remains `queued`;
- the first claim is non-null, names the exact generation-2 task ID, and the fetched task generation is exactly 2;
- generation-1 aggregates remain exactly `(500,600,700)` with one live reservation; the separate blocked-zero and full-reservation legacy projections also retain their exact evidence;
- changing generation 1 back to unsafe `ready_for_human/accounting_blocked=false` makes readiness `not_ready`; restoring `superseded/accounting_blocked=true` makes it `ready`; removing only the quarantine marker again makes it `not_ready`, and restoring the marker recovers readiness;
- a second migrator invocation returns `()`, proving replay rather than merely checking the migration version.

Migration 011 implements the corresponding evidence-preserving branch: an unsafe old `ready_for_human` row with a newer same-identity generation becomes `superseded`; other unsafe claimable or human-ready legacy projections become `needs_human`; all are marked `accounting_blocked` and no reservation, aggregate, run, attempt, usage or audit evidence is deleted or rewritten (`factory/src/adaptive_factory/resources/011_legacy_accounting_quarantine.sql:1-27`). Readiness accepts retained accounting on a superseded row only while the explicit blocked marker remains; the test exercises both sides of that predicate (`factory/src/adaptive_factory/store.py:80-96`).

## Migration, bootstrap and prior behavioral coverage

The current test set retains direct coverage for the earlier M4 blockers and acceptance boundaries:

| Area | Exact behavioral evidence | Result |
| --- | --- | --- |
| Migration chain/replay | Contiguous checksum-locked migrations 001-011; real 008-to-current upgrade; exact `[9,10,11]`; empty replay; migration marker test includes the new superseded branch. | PASS |
| Bootstrap/readiness | Shipped local bootstrap provisions and uses the effective runtime login; upgraded schema reports runtime readiness only when schema, capacity and accounting are consistent. | PASS |
| Authority/TOCTOU | Both observation and exception paths cover revoke-before-validation rejection and revoke-after-validation serialization through commit. | PASS |
| Cleanup/budgets | Release, reconcile and cancel at exhausted ordinary-event budget perform mandatory cleanup exactly once; event, repair and database-deadline exhaustion fail closed. | PASS |
| Accounting/idempotency | Cross-attempt reservations force recovery; exact replay precedes stale-fence checks; changed commands conflict; completion requires settled accounting. | PASS |
| Concurrency/fencing/capacity | Two-worker single-task contention, monotonic fences, late-holder rejection, hidden-allocation fencing, cancel/reconcile lock ordering and exact reader/writer ceilings use real PostgreSQL. | PASS |
| Kill/reconcile bounds | Repository kill is isolated; reconciliation exercises 100+1 paging and an effective transaction `statement_timeout` of exactly `5s`. | PASS |
| Security/audit/indexes | Effective-role negative DML, scoped auth and malformed inputs fail closed; audit-v2 tamper cases fail; populated query plans select named hot-path indexes. | PASS |
| UDS/restart | A real authenticated request crosses the Unix socket; PostgreSQL restart repairs once, replay repairs zero, advances the fence and rejects the late holder. | PASS |

The active-generation recovery ledger records focused PostgreSQL GREEN of 1/1 for the exact upgrade regression, 2/2 for upgrade plus runtime bootstrap, 24/24 dependency-free factory tests, 17/17 installer tests, 63/63 on a fresh disposable PostgreSQL 17 instance plus restart, and 488/488 root tests on product commit `d15302f`.

## Exact-head verification evidence

The inspected fingerprint-bound receipt was created at `2026-09-01T22:11:35Z` for exact HEAD `daa3930cb84ba6547171583e41bcf0dee2ab1314` and tree fingerprint `ad41a13355b097f4be0a3d6c3754b9cc4de8178824e801ac264fad81c852e794`:

```text
14/14 verifier checks: PASS
python-unittest: 488 tests in 492.642s — OK
factory-unit: 24 tests in 0.012s — OK
factory-postgres-exit: 63 tests in 51.339s — OK
restart: one repair; replay no-op; higher fence; late holder rejected — PASS
source-stability: PASS
```

`git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..daa3930cb84ba6547171583e41bcf0dee2ab1314` produced no output. Before this report write, `git rev-parse HEAD` returned the exact reviewed SHA and `git status --short` was empty.

This review changed only this report. It did not modify product code, prior receipts, Git history, databases, external systems, production or Trust CI state. Writing the report changes the evidence-tree fingerprint; the coordinator must bind final review/verification receipts to the resulting final tree before claiming local closure.
