> Provenance: mutation battery for issue #205, run 2026-09-24 in a private scratch copy
> (`/tmp/scope205-work/copy`, a `tar` copy of this worktree excluding `.git`), never in the
> worktree itself. Driver: `run_mutants.py` applies one string-level mutation to the copy, runs
> `python3 -m unittest tests.test_verification_scope -q` in it, and restores the file before the
> next mutant. Target: `tests/test_verification_scope.py` (47 tests). The control run on the
> unmutated copy was `Ran 47 tests ... OK`, so a killed mutant below is a real test signal and not
> a broken harness. This table supersedes the battery in `code-review-205.md`, which was run against
> head `a08060c1` (23 tests) and recorded four survivors.

# Mutation battery — docs/state focused verification lane (issue #205)

| id | mutant | result | note |
| --- | --- | --- | --- |
| — | control (unmutated copy) | OK, `Ran 47 tests` | harness sanity |
| mw1 | `verify()` passes `available_test_targets=[]` | **KILLED** (1 failure) | review survivor: the profile was permanently unreachable in production while the receipt still advertised a classification |
| mw2 | `verify()` passes `status_inventory_trusted=True` | **KILLED** (2 failures) | review survivor: the untrusted-side-channel veto lost its second guard |
| mw3 | `verify()` calls `_python(root, mode, None)` | **KILLED** (1 failure) | review survivor: feature dead while the report claims the focused profile; caught by the `verify()`-level marker-file arm |
| mp1 | delete the `tests/` guard from `_classify_path` | **KILLED** (4 failures) | review survivor (was reason-code-only); now `test-suite-change` is pinned as a reason code |
| m-docs-wholesale | put `docs/` back as an admitted prefix | **KILLED** (5 failures) | finding 1: shipped-and-executed `docs/bitrix-local-AGENTS.md` and any future executed file under `docs/` |
| m-historical | remove the `evidence/historical-*` refusal | **KILLED** (7 failures) | finding 1: byte-pinned declared-immutable evidence (`tests/test_history.py`) |
| m-prefix-shape | move `engineering/decisions.md` into `DOCUMENT_PREFIXES` | **KILLED** (4 failures) | finding 4: prefix matching admits `engineering/decisions.md.bak` |
| m-unnormalized | drop the normalize-before-match guard | **KILLED** (7 failures) | finding 6: `packages/../../etc/passwd` matches `startswith('packages/')` |
| m-drop-untracked-status | remove `'??'` from `SAFE_FILE_STATUSES` | **KILLED** (1 failure) | finding 5: `'??'` must be reachable, not dead |
| m-no-untracked-records | side channel stops collecting untracked paths | **KILLED** (1 failure) | finding 5: the veto channel must span the whole inventory domain |
| m-skips-underdeclare | `FOCUSED_SKIPPED_CHECKS` back to two entries | **KILLED** (1 failure) | finding 3: the replaced full-suite runner was undeclared in report, receipt, README, AGENTS and AC-2 |
| m-drop-binding-test | remove `tests/test_workflow_sources.py` from the admitted set | **KILLED** (2 failures) | finding 1: admitted content (README's Workflow-sources table) left bound to a check the lane did not run |
| mt1-rename-detection | side channel's worktree/index read uses rename+copy detection | **KILLED** (2 failures) | review's mt1 was killed only in its committed half; the staged half is pinned by `test_a_staged_successor_package_is_not_pushed_out_by_copy_detection` |
| mt1b-rename-default | `util.changed_file_statuses` ignores `rename_detection` | **KILLED** (5 failures) | the shared helper must honour the flag for both reads |
| s1-delete-safe | `SAFE_FILE_STATUSES` gains `'D'` | **KILLED** (3 failures) | review survivor check (was already killed at `a08060c1`) |
| s3-scripts-admitted | `DOCUMENT_PREFIXES` gains `scripts/` | **KILLED** (2 failures) | review survivor check (was already killed at `a08060c1`) |
| tf1-wrong-replaced-runner | skip always names `pytest` as the replaced runner | **KILLED** (1 failure, 2 errors) | finding 3: the disclosure must name the runner this tree would actually have used |
| t7-no-empty-target-guard | remove the empty-focused-target guard | **KILLED** (1 failure) | finding 7: `python -m unittest` with no arguments exits 0 having run zero tests |
| m-trust-not-positive | `status_inventory_trusted is not True` weakened back to `is False` | **KILLED** (2 failures) | an absent trust signal must not read as trusted; pinned both on the pure classifier and on `verify()` with a side channel that reports `None` |
| m-side-channel-never-acts | `verify()` never collects status records for the decision | **KILLED** (5 failures) | the wiring that feeds the veto channel |

Summary: 20 mutants, 20 killed, 0 survived; control `Ran 47 tests ... OK`.

## What each survivor from the review of `a08060c1` is now pinned by

- `mw1`, `mw2`, `mw3` — the four `VerifyDocsStateScopeEndToEndTests` arms run `verify()` itself on a
  real temporary git repository whose route base is the parent commit, and assert on the report: the
  profile, the evidence kind, the reason code, the per-check statuses, and whether the
  `full-suite-executed.marker` file written by a non-admitted suite member exists. A classification
  that is not acted on, or a full run that is not taken, is now a failure.
- `mp1` — `test_a_non_lockstep_test_change_reports_its_own_reason_code` pins the reason code, so the
  guard's disclosure role is tested even though eligibility is full either way.
- The reviewer's `mt1` is now pinned in both reads: the committed-range half by the original
  non-vacuous `C0xx` assertion, and the staged half by a new arm that keeps a staged scaffolded
  package from being vetoed as a copy.
