# Independent test/evidence review — issue #155 continuation

Route `c4e47ea3ced7`; reviewer `test_reviewer`; review date 2026-09-21.
Base `90078959ff816068af374ad42f4bb80fdbaec866`; initial reviewed HEAD
`4a47c76b3fb37fbac430fd209771a695832610d2`, implementation `6b13806d454cada0c63520129baf09056db46408`.

## Current verdict

**PASS for the corrected product and reviewed test evidence.** The NULL-diagnostic
fix passes independent red/green review, and all four replacement PostgreSQL
attempts are completed, verified and bound to the unchanged corrected product.
The initial review was **FAIL**: its message-only regression passed while the
store still attached `ContractError(code="invalid_object")` as both cause and
context. That resolved finding and the earlier measurements remain preserved
below as historical facts. No product files were changed by this reviewer.
Final whole-tree verification and receipt binding remain the controller's next
step; this PASS does not claim those later gates have already completed.

## Direct inspection and checks

- Read the route, engineering contract, adaptive-delivery and verification skills,
  test-reviewer instructions, change requirements, plan, continuation, prior review
  limitations, and the actual base-to-HEAD product/test diff.
- Inspected migration `021`, `semantic_repair.py`, `bind_repair_child`, the changed
  migration tests, both timing fixtures and their negative cases, schema-count
  changes, unchanged disposable runner, and the two skipped-test definitions.
- Independently verified every one of the 18 entries in
  [`continuation-20260921/index.json`](continuation-20260921/index.json), including
  byte counts and SHA256 values. All matched.
- Recomputed the manifest from 3,283 live files using its declared exclusions and
  obtained `e33e5e4846200ca06c3f01b3be48f4e90e9e99e2ad3ac080d7dddd3e8922a9a4`.
  This matched the archived product manifest and every attempt's before/after
  digest. Documentation exclusions are explicit; this is not a whole-tree receipt.
- Copied only tracked factory source/tests into external scratch
  `/home/pall/.cache/agbp-run/p155-test-review-9wbrapn6`, then ran
  `/usr/bin/python3 -B -m unittest -v factory.tests.test_migrations factory.tests.test_contracts`.
  **33 tests passed**, 0.058 s, exit 0. Output and metadata are `focused-tests.log`
  and `result.json` in that scratch directory. No database or full verifier was rerun.
- A separate mocked-store probe in the same unchanged copy confirmed the missing
  assertion: SQL NULL produces the expected `store_returned_null` message, but
  `__cause__` and `__context__` are `ContractError`, cause code `invalid_object`,
  and the formatted traceback includes `invalid_object`. See scratch
  `legacy-null-diagnostic.txt`. This is a concrete failure of diagnostic separation,
  despite the passing message-only test.

## Coverage assessment

The added offline tests meaningfully check the exact one-key rejection envelope,
unknown/hostile reason folding, rejection/binding disjointness, valid-binding
positive control, SQL/Python vocabulary equality, absence of anonymous NULL
returns in `021`, ordered predicate preservation, named clause-group counts,
replay CASE direction, and the frozen `018` bind-function digest. The existing
migration drift tests also remain present. Structural SQL assertions are useful
preservation checks, but do not establish behavioral execution of all 12 SQL
reasons.

The PostgreSQL lifecycle test now asserts named `child_limits_exceeded`,
`deadline_exceeded`, and `authority_not_fresh` store failures. The latter is
meaningful: intake validation uses the injected old clock while the task's
`accepted_at` comes from PostgreSQL; the bind therefore sees a proof older than
300 seconds. The direct superseded-child SQL test checks
`child_task_unavailable` and absence of a consumed binding. Existing success and
exact replay assertions remain. All these test methods appear as `ok` in the
archived tier logs; they were not among the skipped tests.

The repair-child fixture samples PostgreSQL time and reduces its inherited budget
by a 120-second safety margin. It still calls the real bind and keeps deliberately
over-wide deadline/limit cases. This addresses bounded fixture scheduling delays;
it is not a guarantee against arbitrary process suspension. The HTTP test stamps
and persists its proof at request construction, retains real request-time
validation, and explicitly rejects a 400-second-old proof with HTTP 422
`stale_m0`. Production `contracts.py` still rejects negative age and age over 300
seconds; `021` retains the original inclusive SQL 0–300-second checks.

The disposable runner is unchanged: bound PostgreSQL 17 identity preflight,
ordinary full factory suite, actual restart/reconciliation probe, and exact-owned
container cleanup remain mandatory. The suite's 480-second timeout is unchanged
and remains asserted by the offline harness test. Product timeouts, clocks,
contract schemas, and migration resources `001`–`020` were not changed. Current
schema-count stubs track `discover_migrations()`; fixed-prefix cases still name
their expected versions, and the inventory test independently pins contiguous
versions 1–21. Thus readiness assertions still compare packaged schema with the
database and do not silently accept an older schema.

## Actual archived runs and limitations

The initial full verifier reports PASS on the initial reviewed HEAD, with stable
whole-tree fingerprint `47e8786408161ac022726c66045b006df1cb07e32d60a4375d7c9889aeab2f3d`:
785 root tests, 80% coverage against the unchanged 74% requirement, 56 selected
factory unit tests, and a disposable tier reporting 779 tests with two skips.
The pilot suite reports 44 tests with its explicit pinned-local-Codex-sandbox
case skipped; workflow-artifacts is not configured. These are not claims that
every optional environment branch ran.

The four archived consecutive disposable attempts all exited 0, with wall times
353.544 / 353.178 / 355.034 / 360.154 seconds. Each reports 779 tests, the same two
skips, exact runtime/attestor roles, and two actual PostgreSQL restarts with
reconciliation. Their product digests and log hashes match. The subsequent NULL
fix changed product/test bytes, so this completed streak remains historical;
it does not establish AC-005 for the corrected product. The replacement evidence
below does.

The two factory-suite skips are specifically:

1. `FreshClusterArtifactAttestorMigrationTests.test_unsafe_role_or_membership_rolls_back_then_absent_role_is_created_least_privilege`:
   requires a separately supplied empty PostgreSQL cluster with the capability
   role absent. The ordinary disposable cluster does not supply that fixture.
   Its schema-count update was inspected but this special role-creation/rollback
   branch was not executed in these runs.
2. `PdfWorkerWithoutParser.test_worker_executes_and_reports_parser_unavailable`:
   the pinned `pypdf 6.18.1` is present, so its absent-parser branch is inapplicable.
   No skip was introduced by this change.

Deferred **#166** is a missing shipped regression starting from exactly the
`001`–`020` prefix and upgrading to `021`, including retained semantic repair
rows. Existing populated lower-prefix upgrades run through `021`; the literal
20→21 historical claim rests on the disclosed scratch experiment. This review
does not turn that into an automated exact-prefix guarantee or a newly observed
upgrade failure, and does not expand this repair to implement #166.

The archived root-suite diagnosis and baseline/red/green scratch logs demonstrate
that an unowned source-like scratch file can fail the architecture seed test.
The current unchanged root source passes. The original failed root traceback was
not preserved, so historical attribution to scratch placement remains an
inference, not a recovered exact failure.

Local tests/review are preflight evidence only. Final whole-tree receipts and the
external App-owned exact-head Trust CI remain the controller's delivery gates.

## Corrected-product delta

Reviewed HEAD `d6595584649827baff78c2be46f978473d4b0465`. Independently recomputed
the live 3,283-file product manifest:
`7bc1176912c7468329d825a1b5f1ef74b0025cc862505f04003050bca1aeac25`.
The only factory changes since the initial reviewed HEAD are `store.py` and
`test_migrations.py`; no SQL resource, timing fixture, timeout, or production
guard changed.

The store now classifies `None` before calling `from_dict`, so the refusal creates
no parser exception. The existing regression covers legacy NULL, the exact
deadline-rejection envelope, and a malformed mapping. Both refusal paths assert
no cause/context and no `invalid_object` in the formatted exception; malformed
data still asserts a real `ContractError` cause. This closes the observed gap
without suppressing real parser failures.

Verified all nine entries in
[`null-cause-review-fix/index.json`](null-cause-review-fix/index.json), including
the original raw hashes and byte lengths of both lossless base64 wrappers.
The archived RED fails specifically at the NULL cause assertion, then GREEN and
all 24 migration tests pass. Independently repeated this control in external
scratch `/home/pall/.cache/agbp-run/p155-test-delta-4xa9pvd8`: the new test with
the old store fails at that same assertion (one test, exit 1); restoring only
the corrected store produces **33 migration/contract tests PASS**, 0.061 s,
exit 0. `red.log`, `green.log`, and `results.json` retain the exact commands and
log hashes there.

Inspected the corrected full verifier result at
`/home/pall/.cache/agbp-run/p155-final-20260921/verify-initial.json`, created
2026-09-21 05:22:11 UTC: **PASS**, fingerprint
`b77fcdb933fc0b74524929a3c25e49de3f3df09c121d2a3a7029ea957785fa4c`.
It reports 785 root tests and 1,098 subtests passed, 80% coverage, 56 selected
factory unit tests, and 779 factory-tier tests with the same two disclosed
skips and the real role/restart probe. This is an actual completed result on
the corrected product, preceding the final documentation/receipt refresh.

The rewritten recovery plan correctly preserves the recorded `001`–`021`
prefix and requires a new versioned correction where SQL replacement is needed;
it no longer promises that reverting the package will replay `018`. Its required
future incremental recovery test is explicitly a prerequisite for that future
correction, not claimed as a test already executed by this change.

At the initial delta observation only two replacement attempts were complete;
the final evidence review below closes that remaining requirement.

## Final corrected-product evidence

Independently verified all nine entries in
[`final-20260921/index.json`](final-20260921/index.json), including each archived
file's SHA256 and byte count, and read the archive's scope statement. Recomputed
the live manifest again after documentation/archive changes: all 3,283 included
files still produce
`7bc1176912c7468329d825a1b5f1ef74b0025cc862505f04003050bca1aeac25`.

[`postgres-streak.json`](final-20260921/postgres-streak.json) records four
sequential successful attempts from 05:10:02 to 05:34:42 UTC on 2026-09-21.
All have exit 0 and identical corrected-product digests before and after. Each
referenced full log independently matches its recorded hash.

| Attempt | Wall seconds | Factory tests | Result |
| --- | ---: | ---: | --- |
| 1 | 358.330 | 779 | OK, two disclosed skips |
| 2 | 375.076 | 779 | OK, two disclosed skips |
| 3 | 378.336 | 779 | OK, two disclosed skips |
| 4 | 366.498 | 779 | OK, two disclosed skips |

Read all four logs for their final summaries, skip identities, bound PostgreSQL
identity preflight, exact runtime/attestor roles, two actual restarts, and
reconciliation success. Also checked that the HTTP intake, semantic lifecycle
with named rejection cases, and repair-function index test methods each end in
`ok` in every log. The skip identities are exactly the two environmental cases
described above; these results do not claim those optional branches ran.
Per-attempt load averages and timestamps are retained in the streak record.

The archived corrected
[`verify-initial.json`](final-20260921/verify-initial.json) is the same completed
PASS checkpoint inspected above. The archive clearly distinguishes that
`d6595584649827baff78c2be46f978473d4b0465` checkpoint from the controller's
forthcoming final documentation commit and whole-tree receipts. The observed
four-pass product requirement is satisfied; no unresolved test-review defect
remains within this change. The disclosed #166 exact-prefix regression gap and
optional environment skips remain limitations, not newly observed failures.
