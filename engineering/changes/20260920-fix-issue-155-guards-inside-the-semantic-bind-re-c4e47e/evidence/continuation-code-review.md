# Independent code review — issue #155 continuation

**Current product review result: PASS** for corrected HEAD `d6595584649827baff78c2be46f978473d4b0465`, product `7bc1176912c7468329d825a1b5f1ef74b0025cc862505f04003050bca1aeac25`. Both findings are resolved by the delta reviewed below; no unresolved code-review finding remains. This report is local review evidence, not merge authority or a claim that final route closure is complete.

**Initial result: FAIL / changes requested** for `4a47c76b3fb37fbac430fd209771a695832610d2`. The initial findings and evidence are preserved below, followed by the corrective review.

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

The controller acknowledged both findings and assigned the NULL repair to the existing write owner and recovery-document correction to documentation closure. The initial verdict remains **FAIL for `4a47c76…`** as historical evidence; the resulting correction is reviewed separately below. Product changes invalidate a snapshot's review and require fresh product evidence; final documentation closure also requires the controller's fingerprint-bound receipt process.

## Corrected delta review — 2026-09-21

**Result: PASS for the corrected product.** Reviewed `4a47c76b3fb37fbac430fd209771a695832610d2..d6595584649827baff78c2be46f978473d4b0465`, including the corrected recovery plan. Independently compared the initial and corrected product manifests: the only changed product entries are `factory/src/adaptive_factory/store.py` and `factory/tests/test_migrations.py`. Recomputed all 3,283 current digest/kind/mode entries and obtained `7bc1176912c7468329d825a1b5f1ef74b0025cc862505f04003050bca1aeac25`, with zero differences from the corrected manifest. SQL resources, guards, grants, fixtures and harness remain exactly as reviewed initially.

### Finding resolution

- **CR-155-01 resolved.** The legacy NULL check is now before `try` / `RepairChildTaskBindingV1.from_dict`. It raises `store_returned_null` without generating a contract exception. The malformed-payload path still raises its store error from the actual parser failure. The existing regression now inspects cause, context and formatted traceback for legacy NULL and the exact deadline envelope, and preserves a `ContractError` cause for the malformed mapping. An independent mocked-store probe also verified serialized JSON `null` and successful binding responses.
- **CR-155-02 resolved.** The recovery plan explicitly retains byte-identical resources 001–021, explains why older source cannot restore the SQL function, and uses the next unused additive migration when the body must change. It retains compatible Python handling, requires an already-migrated 001–021 recovery test, and stops on an unapplied/failed 021. It no longer claims that replaying 018 or deploying the shorter package performs recovery. No future migration or production recovery execution is claimed.

### Corrected evidence checked

Executed by this reviewer:

1. `PYTHONPATH=factory/src python3 -B -m unittest factory.tests.test_migrations -v` — **PASS**, 24 tests, 0.051 s, exit 0.
2. `git diff --check 4a47c76b3fb37fbac430fd209771a695832610d2..HEAD` — **PASS**, exit 0, no output, at `d659558…`.
3. Read-only mocked-store probe — **PASS**: legacy NULL, serialized `null`, and an exact refusal envelope have no exception cause/context and no `invalid_object` traceback frame; a malformed list retains `ContractError.code == 'invalid_object'`; a valid binding is returned unchanged.
4. Read-only archive verification — **PASS**, all nine entries of `null-cause-review-fix/index.json` match their recorded bytes and hashes. Both base64 wrappers decode to their recorded original lengths and SHA256 values. The decoded RED log reproduces the NULL-specific contract-cause assertion failure, and the decoded `change.patch` exactly matches the current two-file product delta. The archived GREEN log reports the targeted test passing. These RED/GREEN commands were executed by the write owner, not rerun as a mutation by this reviewer.
5. Manifest comparison/recomputation — **PASS**, exactly the two expected product entries changed since the initial review and all corrected current entries match, as described above.

Inspected the controller's corrected `/home/pall/.cache/agbp-run/p155-final-20260921/verify-initial.json`: full verification reports **pass**, created `2026-09-21T05:22:11+00:00`, full-tree fingerprint `b77fcdb933fc0b74524929a3c25e49de3f3df09c121d2a3a7029ea957785fa4c`. Root tests, coverage, factory unit tests, mandatory PostgreSQL exit evidence and source stability all pass; unconfigured workflow artifacts remain explicitly skipped. This is supplied execution evidence, not a reviewer-run full suite.

At this delta review's evidence read, the fresh `postgres-streak.json` still reports `running` with **two of four** recorded attempts, both exit 0 on the corrected product identity before and after execution (358.330 s and 375.076 s). The initial four-pass streak is historical and is not reused for this product. Completion of AC-005 and final whole-tree receipts remains with the controller; this code-review PASS does not assert that those outstanding steps have already completed.

Only this report was updated. No product/test/config edits, full database or verifier reruns, credentials, operational actions or local receipts were performed during the corrective review.
