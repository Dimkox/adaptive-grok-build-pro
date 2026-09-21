# Independent data review — issue #155 continuation

Reviewer: route-selected `data_reviewer`, read-only except this report. Route: `c4e47ea3ced7`.

## Current disposition

**PASS for data review** on head `d6595584649827baff78c2be46f978473d4b0465`, product digest `7bc1176912c7468329d825a1b5f1ef74b0025cc862505f04003050bca1aeac25`. D1 is resolved by the revised recovery procedure. The exact reviewed delta and replacement verification are recorded below; the original finding remains as history. This is not a claim that final AC-005, delivery, or operational recovery is complete: the replacement four-pass streak had two completed passes at the delta review.

## Initial disposition and identity

**Initial disposition: FAIL, superseded by the resolved delta review below.** No blocking SQL, migration-history, locking, or data-integrity defect was found in migration 021. The recovery instructions at the initially reviewed head are not executable against an upgraded database.

- Base: `90078959ff816068af374ad42f4bb80fdbaec866`.
- Initially reviewed head: `4a47c76b3fb37fbac430fd209771a695832610d2`.
- Initial product manifest: `e33e5e4846200ca06c3f01b3be48f4e90e9e99e2ad3ac080d7dddd3e8922a9a4`.
- Migration 018 SHA-256: `33053563dce7c34edfa9301130272adb34651d44dd1f2bc305ba3eec01382c70`.
- Migration 021 SHA-256: `868bc21f47351f92b79acb8bd8e9390c62b43803c0b5761400e32c7143d56d5e`.

The controller has announced a separate Python NULL-diagnosis correction and recovery-document edits. The initial verifier and four-pass streak below therefore must not be promoted into final-product evidence after that correction. An addendum will record the actual delta and replacement evidence.

## Finding requiring correction

**D1 — Medium / P2 — Plain source rollback cannot restore this migrated database.** At the initially reviewed head, `rollback.md:15` says reverting the merge and reapplying older source restores the previous function through the normal migration mechanism; `rollback.md:25` calls the resulting applied-021 state harmless. `factory/src/adaptive_factory/migrations.py:74` rejects any applied prefix longer than the packaged resources, and line 79 never reruns an applied migration. A plain revert removes 021 from the package: an already-upgraded database then fails with `MigrationError("applied migration is missing from package")`, while the database function remains the 021 body. The same error prevents the claimed ordinary update from completing; reapplying 018 is not a supported restoration path.

Independently executed, database-free reproduction using the real planner and discovered resources:

```text
plan(available 001–021, applied 001–020): [21]
plan(available 001–021, applied 001–021): []
plan(available 001–020, applied 001–021): MigrationError applied migration is missing from package
```

Required correction: retain byte-identical 001–021 and use a separately reviewed additive forward migration for any function restoration/correction. If describing an application-only rollback, preserve that migration inventory and state its response-shape compatibility explicitly. Do not delete ledger rows, edit 018/021, or claim a fresh-cluster run proves recovery of an already-upgraded history. The controller accepted this finding; correction confirmation remains pending in this initial report.

## SQL and migration assessment

1. **History and application are additive.** I compared every 001–020 resource byte-for-byte with the exact base using `git show`; all 20 match. `migrations.py:48` discovers contiguous numbered SQL resources, hashes their bytes, and `migrations.py:69` compares every applied `(version,name,sha256)` before returning the unapplied suffix. The runner itself is unchanged. At `migrations.py:200`, application, metadata insertion, and role validation share a transaction under the unchanged advisory lock and 5-second lock/statement timeouts. A failed replacement does not commit a successful 021 ledger entry. Resource 021 creates no table/index/backfill and contains no top-level application-data mutation; the migrator records one new ledger row.

2. **No accept/reject weakening found.** I extracted and diffed the complete 018 and 021 `semantic_bind_repair_child` bodies. Changes are `CREATE OR REPLACE`, fixed rejection-envelope returns, and three boundaries splitting the old 49-disjunct block into 32 lineage, 2 freshness, 2 deadline, and 13 limit conditions (`021:127`). Predicate text, casts, lookups, successful insertion, and exception classes remain unchanged. For SQL three-valued conditions, sequential rejection when any group is true preserves rejection when their OR is true; null/false groups still do not reject by themselves. The same caught cast/constraint failures remain rejections. Diagnostics for multiple failures can differ with the first reached guard; this does not add an acceptance path. There are 70 measured guard clauses and 12 emitted SQL reason codes.

3. **Replay, atomicity, and tenant checks remain intact.** At `021:64`, the proposal row lock precedes the same repository/source advisory lock and child-task row lock. The matching stored binding is returned only under the same digest/task/intent/body comparisons (`021:90`); mismatches now name `binding_conflict`. Unique binding constraints and foreign keys remain those in `018:153`. Repository identity, authority identity/revocation, parent lineage, freshness bounds, deadlines, and budget bounds are unchanged. The only successful business write remains the binding insert (`021:212`), inside the same exception-handled function; rejected writes retain the existing rollback behavior.

4. **Privileges and lookup cost are unchanged.** Signature `(char,text) -> jsonb`, `SECURITY DEFINER`, and `search_path=pg_catalog,factory` are identical (`018:1335`, `021:30`). PUBLIC revoke and coordinator-only grant are identical (`018:2119,2149`, `021:225`). No new function signature, role, schema exposure, or dynamic SQL is introduced. Existing proposal/binding primary and unique keys, task source/generation index, intent keys, and observation unique key support the same reads. There is no new table access or index work; the additional work is small fixed JSON construction on refusals. This is source-based query/lock reasoning, not a production EXPLAIN, capacity, or contention measurement. Catalog DDL can still wait or hit the runner's existing timeouts; no production zero-downtime guarantee is established.

5. **Signals are bounded.** The SQL reasons are fixed codes rather than stored row content. The Python reader accepts only the single-key envelope and folds unknown values to a fixed code. Reason precision gives an authorized coordinator more refusal information, as recorded by the security review; repository isolation predicates are unchanged. This review makes no production telemetry or deployment claim.

## Evidence actually executed or inspected

- Executed the byte comparison of all 001–020 resources and complete extracted-function diff described above; no unexpected executable SQL change found.
- Executed four database-free shipped tests with `python3 -B`, adding only `factory/src` to the import path: `MigrationTests.test_repair_child_rejection_resource_is_additive_and_typed`, `test_repair_child_rejection_reasons_match_the_python_allowlist`, `test_repair_child_guard_structure_maps_each_reason_to_one_clause_group`, and `test_missing_renamed_or_checksum_changed_applied_migration_fails`. Result: **4 tests passed in 0.015 s**. These check resource shape, vocabulary, guard grouping/replay arm, frozen original function bytes, and drift refusal.
- Executed the real `plan_migrations` prefix/idempotency/removed-resource probe above. It performs no database connection or migration.
- Independently hashed the 3,283 entries in `evidence/continuation-20260921/product-manifest.json`, including modes, against the initial working product: **zero mismatches**. Verified all 18 files in that archive's `index.json` by byte count and SHA-256: **zero mismatches**.
- Inspected the archived `verify-initial.json`: pass on head `4a47c76b3fb37fbac430fd209771a695832610d2`, tree fingerprint `47e8786408161ac022726c66045b006df1cb07e32d60a4375d7c9889aeab2f3d`, source stability pass, and PostgreSQL tier **779 tests / 346.616 s / two skips**, with real disposable-role and two-restart proof. I did not run this verifier.
- Inspected the four archived PostgreSQL logs and streak record. Each exits 0, reports **779 tests with two skips**, and includes disposable identity preflight, effective-role checks, two restarts, and reconciliation/replay proof. Outer durations are **353.544 / 353.178 / 355.034 / 360.154 s**, with the same initial product digest before/after every attempt. These are source-local disposable tests, not production rollout evidence.
- The two skipped branches are `FreshClusterArtifactAttestorMigrationTests` (dedicated empty-cluster URL absent) and `PdfWorkerWithoutParser` (pinned parser installed). No claim is made that either executed. Inspected the surrounding live-test assertions for typed stale-authority/deadline/limit/superseded-child refusal, no binding consumed on superseded refusal, exact replay, row counts, and the unchanged capability privilege matrix.

## Residual limits

`evidence/postgres-evidence.md:199` records a manually observed 001–020 → 021 upgrade without drift. That is a historical, non-shipped scratch observation; I did not repeat it, and it is not a shipped incremental-upgrade regression. Issue #166 tracks that gap. Fresh full application and older-version upgrade tests do not substitute for the exact incremental path. There is no exhaustive truth-table or production-volume measurement. The fixed 120-second fixture margin is ample for the measured runs but cannot prove immunity to unbounded host suspension.

This report authorizes no database operation, rollout, merge, or external write. I read no credentials or `.env`, called no database/runtime endpoint, and changed only this report. Final disposition requires D1 correction confirmation and review of the announced product delta with refreshed evidence.

## Delta review — D1 resolved

Compared the exact range `4a47c76b3fb37fbac430fd209771a695832610d2..d6595584649827baff78c2be46f978473d4b0465` and the current recovery document. The only `factory/` changes are `store.py` and its `test_migrations.py` regression. Independently compared all 21 SQL resources against the initially reviewed head: **001–021 are byte-identical**, preserving the initial SQL, query, lock, privilege, and migration-history conclusions.

**D1 resolution:** `rollback.md:14` now requires the unchanged 001–021 inventory, explains that earlier 018 never reruns, and rejects the shorter-package revert procedure. Lines 27–41 require one corrective release with the next unused additive resource when SQL must change, preserving signature, `SECURITY DEFINER`, search path, coordinator grant, and compatible Python handling. Lines 43–45 require stopping and checking the unchanged prefix after a failed 021 transaction. Lines 49–59 require future recovery evidence starting from a database already recording 001–021, with prefix hashes, expected appended migration, accepted binding, exact replay, refusals, role isolation, and normal verification. They explicitly do not claim that a future corrective migration has been exercised. This addresses the demonstrated planner failure without changing history or authorizing an operation. **No remaining blocking data finding.**

The Python delta at `store.py:752` rejects legacy SQL NULL before `RepairChildTaskBindingV1.from_dict`; no database statement, transaction, or data-write behavior changes. Its regression now asserts that both NULL and named refusals have no parsing exception cause/context and no `invalid_object` in formatted traceback, while malformed documents retain a `ContractError` cause. I executed that database-free test plus the four migration tests listed above: **5 tests passed in 0.026 s**.

Independently checked all **3,283** entries of `/home/pall/.cache/agbp-run/p155-final-20260921/product-manifest.json` against current file contents and modes, then recomputed its canonical manifest digest: **zero mismatches**, digest `7bc1176912c7468329d825a1b5f1ef74b0025cc862505f04003050bca1aeac25` matches the recorded identity.

Inspected `/home/pall/.cache/agbp-run/p155-final-20260921/verify-initial.json`: **PASS**, created `2026-09-21T05:22:11+00:00`, head `d6595584649827baff78c2be46f978473d4b0465`, tree fingerprint `b77fcdb933fc0b74524929a3c25e49de3f3df09c121d2a3a7029ea957785fa4c`, source stability pass. Its PostgreSQL tier reports **779 tests / 356.009 s / two skips**, with disposable identity, effective-role, actual two-restart and reconciliation proof. I did not rerun the verifier or connect to a database. The same skipped-branch and exact incremental-upgrade limitations from the initial review remain.

At this delta review, the replacement `postgres-streak.json` remains `running`, with two completed exit-0 attempts (**358.330 / 375.076 s**) carrying the corrected product digest before/after each. The controller must retain and inspect the completed replacement streak for AC-005; the initial four-pass streak is historical. Later documentation-only changes need final receipt binding, and any product change requires renewed affected verification/review.
