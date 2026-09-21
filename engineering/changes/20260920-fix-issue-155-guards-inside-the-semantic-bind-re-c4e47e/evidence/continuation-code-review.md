# Independent code review — issue #155 continuation

**Result: FAIL / changes requested.** Two P2 findings remain on the reviewed snapshot. This report is local review evidence, not merge authority.

## Identity and scope

- Reviewer: route-selected `code_reviewer`, independent of the implementation owner.
- Route: `c4e47ea3ced7`.
- Base: `90078959ff816068af374ad42f4bb80fdbaec866`.
- Implementation: `6b13806d454cada0c63520129baf09056db46408`.
- Reviewed HEAD: `4a47c76b3fb37fbac430fd209771a695832610d2`.
- Reviewed product manifest: `e33e5e4846200ca06c3f01b3be48f4e90e9e99e2ad3ac080d7dddd3e8922a9a4`, 3,283 entries. Independently recomputed the manifest using each entry's content digest, kind and mode; all entries and the aggregate matched before the requested repairs.
- Scope: actual base-to-HEAD product/test diff, migrations 018/021 and migration runner, rejection decoder, store classification, integration fixture callers, typed change specification and recovery instructions. Read the contract, active route, delivery skill, selected workflow skills and reviewer role. Historical review reports were not used as authority.

## Findings

### CR-155-01 — P2: legacy NULL still creates the misleading contract-error frame

Location: `factory/src/adaptive_factory/store.py:759` (the classification occurs after `from_dict` at line 753).

For a database that has not applied 021, a guard refusal still returns SQL NULL. The new compatibility branch changes the outer message to `semantic repair child binding rejected: store_returned_null`, but first calls `RepairChildTaskBindingV1.from_dict(None)` and then raises the store error `from exc`. The cause is therefore still `ContractError` with code `invalid_object`, and a normal formatted traceback includes that misleading shape-error frame. This contradicts AC-002/SIG-001 and the documented no-go condition that a refusal must not reach `invalid_object` without a malformed payload.

A read-only mocked connection reproduced:

| SQL response | Outer message suffix | Cause code | `invalid_object` in traceback |
| --- | --- | --- | --- |
| `None` | `rejected: store_returned_null` | `invalid_object` | yes |
| exact deadline envelope | `rejected: deadline_exceeded` | none | no |
| malformed list | `payload is malformed` | `invalid_object` | yes |
| exact envelope with unknown text | `rejected: binding_rejected` | none | no |

The existing `test_bind_repair_child_separates_an_unexplained_store_refusal` passes because it examines only `str(exception)`. Classify NULL before invoking `from_dict`; assert the absence of both a contract-error cause/context and an `invalid_object` traceback frame for this refusal. Keep the malformed-payload cause intact.

### CR-155-02 — P2: the documented source-only rollback cannot migrate a database containing 021

Location: `engineering/changes/20260920-fix-issue-155-guards-inside-the-semantic-bind-re-c4e47e/rollback.md:15`, with the conflicting assertion at line 25.

The instructions say that reverting the merge and reapplying the older source restores the old SQL body. Migrations are append-only: 018 will not run again, and a package containing only 001–020 cannot plan against a database that recorded 021. A pure in-memory call to `plan_migrations(available[:20], applied_001_through_021)` raised `MigrationError: applied migration is missing from package`. Following this recovery instruction would introduce a migration/startup failure instead of restoring the function.

Retain the immutable 001–021 prefix and describe a separately reviewed additive corrective migration, together with compatible Python behavior and upgrade-path verification. Do not describe an old-source apply as SQL recovery, or delete migration history.

## Checks and observations

Executed by this reviewer on the identified snapshot:

1. `PYTHONPATH=factory/src python3 -B -m unittest factory.tests.test_migrations -v` — **PASS**, 24 tests, 0.047 s, exit 0. This passing suite does not cover CR-155-01's exception chain.
2. `git diff --check 90078959ff816068af374ad42f4bb80fdbaec866..HEAD` — **PASS**, exit 0, no output.
3. Read-only Python comparison of every migration 001–020 against `git show <base>:<path>` — **PASS**, 20 byte-identical resources.
4. Independent whole-function comparison — **PASS**: replacing only the twelve new reason objects with NULL, changing `CREATE OR REPLACE` back to `CREATE`, and joining the three new contiguous guard boundaries reproduces the original 018 function after whitespace normalization. This comparison retains the successful replay CASE arm, queries, locks, insertion and exception handler; it does not discard arbitrary guard lines. Measured nine original NULL-returning paths and twelve new reason sites.
5. Manifest recomputation — **PASS**, all 3,283 entries and aggregate matched the product identity above. An initial reviewer probe mistakenly compared digest strings with manifest metadata objects and exited 1; after inspecting the schema, the corrected probe compared digest/kind/mode objects and found zero changes. The initial failure was a reviewer-probe error, not product drift.
6. Mocked store probe — **CONFIRMED CR-155-01**, exit 0. It used only `MagicMock`, `patch.object(store, '_connect', ...)`, a synthetic binding and the four response values in the table; no database connection was made.
7. Migration-planning probe — **CONFIRMED CR-155-02**, exit 0 after observing the expected `MigrationError`; no database mutation was made.

Additional review conclusions:

- The twelve SQL reason literals match the closed Python vocabulary, excluding its fixed unknown-code fallback. The exact one-key envelope check rejects extra keys; unknown or non-string values fold to `binding_rejected` without echoing source text.
- Splitting the 49-clause OR block into contiguous lineage/freshness/deadline/limits groups preserves the acceptance predicate, including SQL NULL handling. Earlier true groups return before later groups; this gives intentional diagnostic precedence without adding accepted rows.
- The signature, `SECURITY DEFINER` search path, coordinator grant and public revoke are retained. There are no new tables, indexes, row rewrites or contract/schema changes.
- Child deadline fixture headroom and request-time HTTP authority stamping stay in tests. The over-wide deadline/limits refusals and 400-second stale-authority refusal remain asserted. The disposable-exit harness and product freshness window are unchanged.
- The diff under `factory/contracts/`, `schemas/`, `architecture/`, `governance/` and `factory/tests/run_disposable_exit.py` is empty.

## Supplied execution evidence inspected

These commands were run by the controller, not this reviewer:

- `/home/pall/.cache/agbp-run/p155-continuation-20260921/verify-initial.json` reports the full `python3 scripts/grok_verify.py --mode pr --json` as **pass**, fingerprint `47e8786408161ac022726c66045b006df1cb07e32d60a4375d7c9889aeab2f3d`. Its checks include root tests, factory unit tests, the mandatory PostgreSQL tier and source stability; workflow artifacts are explicitly unconfigured/skipped.
- Independently checked the four archived PostgreSQL log hashes against `continuation-20260921/postgres-streak.json`, their per-attempt product identities and their result summaries. All four recorded exit 0 on product `e33e5e48…`; durations were 353.544, 353.178, 355.034 and 360.154 seconds. Each log reports 779 tests, `OK (skipped=2)`, two actual PostgreSQL restarts, effective capability roles, recovery and final disposable-tier PASS.
- Those successful runs establish the recorded snapshot's behavior; they do not remove the two findings, and must not be relabeled as verification of a later product repair.

## Limits and disposition

No product/test/config edits, database suite runs, credentials, external writes, receipts or operational approvals were performed by this reviewer. Only this report was written. No exhaustive live database exercise of all twelve named reasons was added; the live evidence, focused tests, predicate comparison and independent probes have the limits stated above.

The controller acknowledged both findings and assigned the NULL repair to the existing write owner and recovery-document correction to documentation closure. This report remains **FAIL for `4a47c76…`** until the resulting diff and new verification evidence are reviewed. Product changes invalidate this snapshot's review and require fresh product evidence; final documentation closure also requires the controller's fingerprint-bound receipt process.
