# Review response — interrupted Trust CI commands (#103)

Round 1: code review **PASS** (3 factual record defects F1/F2/F4 + one disclosure check F3) and test review
**PASS** with mutation-tested gaps **G-1 Major, G-2 Major, G-3/G-4 Minor** on `2f66ba6` + this branch.
Round 2 (code review PASS, two residuals): **R2-1** (my *corrected* F1 citation attributed `001-018` to a
document that does not contain it) and **R2-2** (totality closed for `exit_code` but not for `stderr_tail`).
Everything below is dispositioned as measured, not asserted; nothing was rejected on argument alone.

| # | Finding | Disposition | Evidence (command → result) |
| --- | --- | --- | --- |
| G-1 (Major, test review) | `classify_command_abort` was not total; totality rested on the single guard in `runner._first_command_abort`, so `MU6` survived, and a signed-but-malformed replay row could reach it (`AttestationPayload.from_dict` only wraps each row with `dict(item)` at `models.py:329` — no per-field type check) | **Accepted, fixed.** Type rejection moved into the classifier (`sandbox.py:86`); the runner check (`runner.py:273`) stays and is now documented as a second, independent layer. | Before: `classify_command_abort(name='unit', exit_code=None)` → `TypeError`, `'137'` → `TypeError`, **`137.0` → `CommandAbort(signal_number=9.0)`**. After: all of `None/'137'/''/True/False/137.0/[]/{}/object()` → `None`. `MU6b` (delete the classifier check) → `FAILED (failures=1, errors=6)`; **both** layers deleted → `FAILED (failures=2, errors=9)` |
| G-2 (Major, test review) | "a passed/replayed pass records no `failure_code`" was untested; `MU11` survived, so a passed job could be stored with `verification-failed` | **Accepted, fixed (coverage).** Unit + end-to-end + passed-replay assertions added; behaviour was already correct, so no code change claimed. | `test_passed_job_records_no_failure_code_at_all` and `assertIsNone(replayed_job.failure_code)`; `MU11` → `FAILED (failures=2)`. `grep -rn "assertIsNone(.*failure_code" trust-ci/tests/` → was empty, now **4** hits |
| G-3 (Minor) | 129/130 and the `_MAX_SIGNAL_NUMBER` edge unpinned | **Accepted, fixed (pin only).** | `test_signal_range_boundaries_are_pinned`: `129→SIGHUP`, `130→SIGINT`, `192→SIGRTMAX`, `128/193/194/255` → no claim |
| G-4 (Minor) | The timeout marker's `\Z` anchor unpinned: a command printing the phrase mid-stderr with exit 124 would be misread as a sandbox timeout | **Accepted, fixed (pin only).** | `test_timeout_marker_must_end_the_stored_tail`; `MU4` (delete `\s*\Z`) → `FAILED (failures=1)` |
| F1 (code review, record) | `change-spec.yaml`/`release.md` claimed frozen "migrations `001`-`018`" for `trust-ci/sql/`, which holds 3 files | **Accepted, fixed** — but the fix itself carried a new false referent, see R2-1. | `ls trust-ci/sql/*.sql \| wc -l` → `3` |
| F2 (code review, record) | `release.md` told operators that any `aborted-by-signal` row is "an infrastructure event, not a code defect", contradicting `brief.md`/`architecture.md` (a PR-caused in-container OOM also renders as 137) | **Accepted, rewritten.** The record now says the class means "the command reached no verdict", that who signalled is unknown, and that an OOM caused by the PR's own tests is a PR defect to fix, not to re-gate. | `release.md` "Metrics and alerts" section |
| F3 (info, both) | On attestation replay the `aborted-by-timeout` class is unrecoverable (signed rows carry no stderr), falling back to `verification-failed` | **Accepted as disclosure, not as a code change.** Fixing it means widening the signed attestation format (contract/policy/holdout surface), out of scope for a source-only bugfix; the fallback is fail-safe. Now named in the tree, not just in chat. | `requirements.md` "Failure and edge cases", `architecture.md` (`_attested_command_abort`), `test-plan.md` "Manual checks and disclosed limits" |
| F4 (record) | Wording implied the `isinstance(exit_code, bool)` guard protected the classifier | **Accepted, wording corrected.** It is defense-in-depth; totality is the classifier's own contract. | `architecture.md` Decision 6; INV-001 in `change-spec.yaml`/`requirements.md` |
| **R2-1 (round 2)** | My corrected citation attributed `001-018` to `AGENTS.md`, which contains no such number; and `tasks.md` declared the replacement done "everywhere" | **Accepted, fixed.** Rewritten to artifact-anchored form in `change-spec.yaml` INV-002, `requirements.md` INV-002, `release.md`, `tasks.md`; "everywhere" replaced by the grep that was actually run. | `grep -c "018" AGENTS.md` → `0`; `AGENTS.md:130` = "All schema changes use versioned migrations". Real bearers: `PROJECT_STATE.json` `current_unreleased_change.frozen.postgresql_migrations` (261; also 352, 625, `active_delivery.integrated_stack.migrations` 889), `README.md:32`, `START_HERE.md:57`, `CHANGELOG.md:75`. Referent proven by tag, not by reading: `git ls-tree -r --name-only v2.0.13 \| grep -c 'factory/src/adaptive_factory/resources/.*\.sql'` → **18** (last `018_semantic_validation_bridge.sql`), today **20** (last `020_execution_v2_priced_usage.sql`). Residual co-mentions audit (no count is quoted, because the count moves when these very files are edited): `grep -rn "AGENTS.md" <pkg> \| grep -v /evidence/ \| grep 018` lists only lines that refute the attribution or record this correction — no positive attribution remains anywhere in the package |
| **R2-2 (round 2)** | Totality was symmetric for neither input: `classify_command_abort(name='u', exit_code=124, stderr_tail=None)` → `TypeError: expected string or bytes-like object, got 'NoneType'` (`['x']` → `'list'`, `b'…'` → "cannot use a string pattern on a bytes-like object", `5` → `'int'`); with `exit_code=137` the same tails passed only because `and` short-circuits | **Accepted, fixed the same way.** `tail = stderr_tail if isinstance(stderr_tail, str) else ''` before the regex (`sandbox.py:88`), `stderr_tail: Any`, docstring states both halves of the contract: a non-string tail removes *corroboration* (no timeout claim) but never suppresses an exit-status-proven kill. Written test-first: red before the fix. | Before: `Ran 1 test … FAILED (errors=7)` for `test_non_string_stderr_tail_yields_no_claim_instead_of_raising`; after: green. Mutations: MT1 delete the normalization → `FAILED (errors=7, skipped=10)`; MT2 `str(stderr_tail)` → `FAILED (failures=1, skipped=10)`; MT3 accept+decode `bytes` → `FAILED (failures=2, skipped=10)` — arm attribution measured, not assumed: with the `__str__`-object arm removed the test still killed MT3 (`failures=2`) but **survived MT2** (`Ran 1 test … OK`), so that arm exists specifically to refuse `str()` coercion, which a `bytes` arm cannot expose because of `repr` quoting |
| Equivalent-mutant notes | Two mutants are deliberately not chased, and this is not a claim of perfection | `MU6` (delete the runner second-layer guard) stays green because the classifier is now total — behaviour-identical, which is the property the finding asked for. `\Z → $` is identical here since the pattern already allows `\s*` before the end. | Each measured by applying it and re-running the suite, with byte-exact restore (`restored byte-identical: True`) |

## Limits of this response

- Every measurement above ran on this host with `python3 -m unittest` (`pytest` is not installed); the 10
  PostgreSQL-integration skips stay unexecuted, so the durable write of the new `failure_code` through
  `PostgresStore.finish` is still verified only by reading `store.py:416` (`SET status = %s, result =
  %s::jsonb, failure_code = %s`) and by the App check.
- Source-only: the deployed Trust CI service and the stored PR #102 row are untouched by this work, and OOM vs
  outside SIGKILL stay merged in one class (`137`), as disclosed in `brief.md`.

## Round 3 (coordinator-applied, narrow)

`review-test-round3.md` verdict: **FAIL on one record finding**, behaviour PASS. Its item 1 confirmed the
`stderr_tail` totality on the final bytes and independently reproduced the MT2 attribution: without the
`_MarkerSounding` arm MT2 survives (`Ran 1 test … OK`), with it MT2 is killed at `test_ops.py:107`, and MT3
dies either way — the implementer's claim about which arm carries which mutant is therefore accurate rather
than asserted.

**T-1 (blocking, applied by the coordinator, not the write owner).** `tasks.md:65` still quoted a line count
— "(**7** at the time of writing…)" — while the very command it names yields 6, and it was written at 05:44:42,
*after* `review-response.md` (05:42:46) stated that no count is quoted because the count moves. Direct
self-contradiction, same class as R2-1. The parenthetical is deleted and replaced by a properties clause that
cannot move.

Applied by the coordinator because the delta was one false clause in prose, not behaviour; recorded here so
the trail says who changed what after which review. Re-verified after the edit rather than inherited:

```
$ grep -rn "AGENTS.md" <package> --include=*.md --include=*.yaml | grep -v /evidence/ | grep 018
6 lines — tasks.md:58, tasks.md:67, requirements.md:14, release.md:26, test-plan.md:60, change-spec.yaml:99
   every one a negation or a record of this correction; none attributes the range to AGENTS.md
$ grep -c "018" AGENTS.md            -> 0
$ git ls-tree -r --name-only v2.0.13 | grep -c 'factory/src/adaptive_factory/resources/.*\.sql' -> 18
$ ls trust-ci/sql | wc -l            -> 3
$ grep -rn "([0-9]\+ at the time\|([0-9]\+ lines\|→ \*\*[0-9]\+\*\* " <package> --include=*.md | grep -v evidence/
   (empty)
```

No count of package-internal matches is asserted anywhere in this package now. The counts that remain
(`test-plan.md:6` 14→29 / 26→36 / 21→22 = 26 tests; `test-plan.md:36` "4 hits") describe the frozen product
tree at base `2f66ba6` and are refutable only by changing that tree, which is the permitted kind.

Two tooling traps that round 3 surfaced, recorded here because they can silently fake a mutation result and
belong to the factory, not to this change: `python3 -m unittest tests.test_ops` from `trust-ci/` dies with
`ModuleNotFoundError: No module named '_support'` (the suite needs `discover`'s top level), and
`unittest discover -k` matches the *full test id*, so an unanchored pattern such as
`test_non_string_stderr_tail*` reports `NO TESTS RAN` — which reads exactly like a surviving mutant.
