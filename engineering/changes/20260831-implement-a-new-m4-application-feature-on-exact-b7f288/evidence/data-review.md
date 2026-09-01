# M4 exact-final data review — PASS

## Review binding

- Route: `b7f288f1e81e`
- Change: `20260831-implement-a-new-m4-application-feature-on-exact-b7f288`
- Accepted M3 base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Exact reviewed product HEAD: `daa3930cb84ba6547171583e41bcf0dee2ab1314`
- Exact Git tree: `9c93b2ca4fea4f71ab70bbf71bd62ca8df936ad8`
- Full reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..daa3930cb84ba6547171583e41bcf0dee2ab1314`
- Collision-fix range: `04261326e177e6d2014a576d3f4a0fb5feab56be..daa3930cb84ba6547171583e41bcf0dee2ab1314`
- Exact-head verifier: PASS, tree fingerprint `ad41a13355b097f4be0a3d6c3754b9cc4de8178824e801ac264fad81c852e794`
- Reviewer: route-selected read-only `data_reviewer`

## Verdict

**PASS**

- Critical data findings: **0**
- Important data findings: **0**

The two prior schema-008 recovery findings and the later same-identity migration collision are closed. No remaining Critical or Important migration, constraint, locking, accounting, replay, recovery or readiness defect was found in the exact product tree.

## Schema-008 recovery and migration 011

Migration `011` now performs one evidence-preserving, schema-qualified update:

- blocked `queued`/`retry` rows become `needs_human/accounting_blocked`;
- an unsafe `ready_for_human` row with a newer generation under the exact repository/source-type/source-ID identity becomes `superseded/accounting_blocked`;
- a lone unsafe `ready_for_human` generation becomes `needs_human/accounting_blocked`.

The `superseded` branch remains outside the `tasks_one_active_identity` predicate, so upgrading an unsafe generation 1 beside an already-active generation 2 cannot introduce a second index-active row. Migration `011` does not delete or rewrite intents, runs, attempts, reservations, observations, events or audit rows, and it preserves task reservation aggregates. Its exact packaged SHA-256 is `ff358ea06a5497d9d215f8fef7ab3540b0b4af993c806985e9d5ae6d46b01bea`.

The real PostgreSQL regression builds a non-empty database through exact migration `008`, seeds an unsafe generation-1 `ready_for_human` two-attempt history with a live prior-attempt reservation and usage, and seeds generation 2 as `queued` under the same exact source identity. It proves atomic application of `[009,010,011]`, generation 1 at `superseded/accounting_blocked`, generation 2 uniquely claimable, exact reservation aggregates retained, readiness restored and an empty second migration plan (`factory/tests/test_postgres_integration.py:984-1237`).

Readiness independently rejects unsafe accounting on `queued`, `retry` and `ready_for_human`, and rejects a superseded accounting residue if its explicit `accounting_blocked` quarantine marker is removed. It intentionally accepts `needs_human/accounting_blocked` and `superseded/accounting_blocked` as non-claimable recovery states (`factory/src/adaptive_factory/store.py:80-96`). Claim selection still requires a claimable state, an unblocked zero projection and no live task reservation (`store.py:516-523`).

## Migration, constraint and transaction assessment

- Migrations are contiguous `001..011`, checksum-locked and applied in one transaction under a factory advisory lock with five-second lock and statement timeouts. Non-contiguous history, missing packaged history and checksum drift fail closed.
- Migrations `001..010` remain unchanged by the final collision repair. The in-place edit is confined to unreleased migration `011`, which the change ledger binds to disposable local databases only. Any disposable database with the superseded `011` checksum must be recreated; after durable intake recovery is forward-only with migration `012+`.
- Task identity has a durable `(repository_id, source_type, source_id, generation)` uniqueness constraint plus one partial active-generation index. Run/task, allocation/task, reservation/task and observation/task relationships are bound by composite foreign keys; destructive cascades are absent.
- Capacity allocation and release use fixed-search-path, PUBLIC-revoked capability functions, canonical counter-row lock order, ceilings of 20 global readers / 10 repository readers / one writer, underflow checks and exactly-once live-allocation release.
- M0 authority validation uses `FOR SHARE`, which conflicts with non-key revocation updates and holds through intake commit. Claim uses `FOR UPDATE SKIP LOCKED`; reconcile/cancel/release acquire capacity before task/run locks. The real interleaving and deadlock regressions pass.
- Completion requires current-run usage, no task-wide live reservation, zero reserved aggregates and unblocked accounting. Retry with unresolved accounting goes to explicit human recovery. Mandatory cleanup facts are outside the ordinary event budget but remain transactional with run/allocation release and hash-chained audit.
- Command and accounting replay is durable and request-digest bound; exact replay returns the recorded result while a changed command conflicts. Migration replay is checksum verified and empty after `011`.
- Claim, audit, usage, active-reservation and expired-run predicates have matching task-scoped indexes; populated `EXPLAIN (ANALYZE, BUFFERS)` assertions select them. Reconciliation is keyset-bounded to 100 candidates and the transaction-local timeout is exactly five seconds.

Migration `011` is a set-based historical scan/update and can exceed the five-second bound on an unexpectedly large or contended database. In the authorized M4 source/disposable rollout this is not a release blocker; the transaction rolls back atomically, and the documented killed-start, backup/restore comparison and readiness gate make timeout or lock contention a no-go rather than a partial migration.

## Independent verification evidence

- `git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..daa3930cb84ba6547171583e41bcf0dee2ab1314` — PASS.
- `PYTHONPATH=factory/src python3 -m unittest factory.tests.test_migrations factory.tests.test_contracts factory.tests.test_state factory.tests.test_service -v` — PASS, 24/24.
- `python3 factory/tests/run_disposable_exit.py` — PASS, 63/63 in 34.926s on a fresh disposable PostgreSQL 17 container, including the exact schema-008 same-identity upgrade, authority interleavings, accounting/replay, capacity, lock-order and indexed-plan cases.
- The same independent run restarted PostgreSQL, repaired one expired lease, repaired zero on replay, issued a higher fence and rejected the late holder.
- The exact disposable container and temporary environment were removed by the runner. No shared, external, Trust CI or production database was read or mutated.

This review changed only this report. It did not modify product code, migrations, receipts, Git history or external state. Writing final review reports changes the evidence-tree fingerprint; the coordinator must rerun/bind final verification and review receipts to the resulting final evidence tree before claiming local completion.

**Final data-review result: PASS for exact product HEAD `daa3930cb84ba6547171583e41bcf0dee2ab1314`.**
