> Provenance: mutation battery for issue #205, run 2026-09-25 (UTC) against this contour's tree
> after the fixes to the review of head `a08060c1` (see `code-review-205.md`). Method: the worktree
> was copied with `tar` into a private scratch directory outside the repository (excluding `.git`,
> `__pycache__`, `.qwen`); each mutant was applied to that copy only, `python3 -m unittest
> tests.test_verification_scope -q` was run inside it, and the file was restored before the next
> mutant. The worktree itself was never mutated, and no other contour's process was touched.
> Control (unmutated copy): `Ran 47 tests ... OK`, so a KILLED row is a real test signal and not a
> broken harness. Result: 20 mutants, 20 KILLED, 0 survived.
>
> This supersedes the battery recorded in `code-review-205.md`, which ran 23 tests against head
> `a08060c1` and recorded four survivors (`mw1`, `mw2`, `mw3`, `mp1`).

# Mutation battery — docs/state focused verification lane (issue #205)

| id | mutant | what it would let through | outcome | killed by |
| --- | --- | --- | --- | --- |
| `mw1` | `verify()` passes `available_test_targets=[]` | the profile becomes permanently unreachable in production while the receipt still advertises a classification it did not act on | **KILLED** (1 failure, `Ran 47 tests`) | `VerifyDocsStateScopeEndToEndTests.test_verify_selects_and_runs_the_focused_profile_for_a_docs_only_successor` |
| `mw2` | `verify()` passes `status_inventory_trusted=True` | the second status veto is lost silently | **KILLED** (2 failures, `Ran 47 tests`) | `test_verify_refuses_the_lane_when_the_status_channel_is_not_trusted` |
| `mw3` | `verify()` calls `_python(root, mode, None)` | the feature is dead while the report says `docs-state-focused` | **KILLED** (1 failure, `Ran 47 tests`) | the focused end-to-end arm: the full-discovery marker file appears and `python-focused-unittest` disappears |
| `m-side-channel-never-acts` | `verify()` never collects status records for the decision | the whole fail-closed status channel stops feeding the scope decision | **KILLED** (5 failures, `Ran 47 tests`) | the focused end-to-end arm plus the status-channel arms |
| `m-trust-not-positive` | `status_inventory_trusted is not True` weakened back to `is False` | an absent trust signal would be read as a positive confirmation | **KILLED** (2 failures, `Ran 47 tests`) | `test_missing_or_untrusted_status_inventory_fails_closed` and the `verify()`-level `([], None)` arm |
| `mp1` | delete the `tests/` guard from `_classify_path` | a test change loses its reason code (eligibility is full either way) | **KILLED** (4 failures, `Ran 47 tests`) | `test_a_non_lockstep_test_change_reports_its_own_reason_code`, `test_the_lane_tests_themselves_are_not_admitted` |
| `m-docs-wholesale` | restore `'docs/'` as an admitted prefix | any future `docs/` payload rides a five-module lane; only the separately-named shipped file stays refused | **KILLED** (5 failures, `Ran 47 tests`) | `test_an_undeclared_name_under_an_admitted_directory_is_not_admitted`, `test_a_name_outside_every_declared_role_is_not_admitted`, `test_documentation_prefixes_are_directory_shaped_only` |
| `m-historical` | remove the `**/evidence/historical-*` refusal | declared-immutable sha256-pinned evidence is rewritten on the focused lane | **KILLED** (7 failures, `Ran 47 tests`) | `test_declared_immutable_historical_evidence_is_rejected_by_its_own_reason_code`, `FULL_PATH_ONLY_CHANGES` |
| `m-prefix-shape` | put `engineering/decisions.md` back into `DOCUMENT_PREFIXES` | `engineering/decisions.md.bak` and any suffix-glued sibling ride the lane | **KILLED** (4 failures, `Ran 47 tests`) | `test_a_suffix_glued_sibling_of_an_admitted_log_is_not_admitted`, `test_documentation_prefixes_are_directory_shaped_only` |
| `m-unnormalized` | classify before normalization | `packages/../../etc/passwd` matches `startswith('packages/')` inside the classifier | **KILLED** (7 failures, `Ran 47 tests`) | `test_an_unnormalized_path_cannot_escape_the_prefix_rules` |
| `m-drop-untracked-status` | remove `'??'` from `SAFE_FILE_STATUSES` | untracked documentation additions veto the lane, so the safe set no longer matches the channel domain | **KILLED** (1 failure, `Ran 47 tests`) | `test_untracked_paths_arrive_as_status_records_so_the_veto_covers_them` |
| `m-no-untracked-records` | the side channel stops collecting `ls-files --others` | `??` becomes a dead entry and untracked paths reach the classifier record-free | **KILLED** (1 failure, `Ran 47 tests`) | the same untracked arm |
| `m-skips-underdeclare` | `FOCUSED_SKIPPED_CHECKS` back to two entries | the receipt under-declares what did not run (the replaced discovery runner unnamed) | **KILLED** (1 failure, `Ran 47 tests`) | `test_release_sync_inventory_selects_the_focused_profile`, `test_eligible_check_names_every_admitted_path_and_each_skip`, the focused end-to-end arm |
| `m-drop-binding-test` | remove `tests/test_workflow_sources.py` from the admitted set | admitted content (README's Workflow-sources table) is verified by a check the lane does not run | **KILLED** (2 failures, `Ran 47 tests`) | `test_every_admitted_content_class_is_re_derived_by_a_module_this_lane_runs`, `test_focused_command_names_modules_not_discovery` |
| `mt1-rename-detection` | the index/worktree half of the side channel reads with rename+copy detection | a staged scaffolded package reports `C0xx` and every evidence-carrying local gate is pushed to the full suite | **KILLED** (2 failures, `Ran 47 tests`) | `test_a_staged_successor_package_is_not_pushed_out_by_copy_detection`, `test_a_working_tree_rename_reaches_the_lane_as_a_deletion_not_a_rename` |
| `mt1b-rename-default` | `util.changed_file_statuses` ignores `rename_detection` | the reviewer's original mt1: every docs/state read gains `C0xx`/`R100` | **KILLED** (5 failures, `Ran 47 tests`) | `test_a_scaffolded_package_copy_still_selects_the_focused_profile`, `test_the_shared_helper_still_reports_renames_and_copies_by_default` |
| `s1-delete-safe` | `SAFE_FILE_STATUSES` gains `'D'` | a deleted product path behind an admitted name rides the lane | **KILLED** (3 failures, `Ran 47 tests`) | `test_deleted_renamed_copied_and_unmerged_statuses_keep_the_full_profile`, the rename-blind and staged arms |
| `s3-scripts-admitted` | `DOCUMENT_PREFIXES` gains `scripts/` | executed product admitted as prose | **KILLED** (2 failures, `Ran 47 tests`) | `test_every_executable_or_contract_bearing_path_keeps_the_full_profile` |
| `tf1-wrong-replaced-runner` | `_python` always names `pytest` as the replaced runner | the skip advertises a runner this tree never would have used | **KILLED** (1 failure, 2 errors, `Ran 47 tests`) | `test_the_replaced_runner_is_named_by_the_caller_not_assumed`, `test_admitted_inventory_never_executes_full_suite_discovery` |
| `t7-no-empty-target-guard` | `_focused_python`'s empty-target guard disabled | an empty module list is handed to `python -m unittest`, which runs zero tests and whose exit status is interpreter-dependent (measured here: exit 5 `NO TESTS RAN` on 3.12.3 and 3.14.6) instead of the profile reporting exactly what it refused to run | **KILLED** (1 failure, `Ran 47 tests`) | `test_an_empty_target_list_fails_instead_of_reporting_a_green_zero_test_run` (fails on the refused check carrying no command) |

## Review survivors, one by one

- `mw1`, `mw2`, `mw3` (finding 2) — four `VerifyDocsStateScopeEndToEndTests` arms run `verify()`
  itself against a real temporary git repository whose route base is the parent commit, and assert on
  the report: `docs_state_scope.profile`, `evidence_kind`, `reason_code`, the per-check statuses, and
  whether `full-suite-executed.marker` — a file only a non-admitted suite member can write — exists.
  A classification that is never acted on, and a full run that pretends otherwise, both fail.
- `mp1` (finding 7's note) — `test-suite-change` is now pinned as a reason code, so the guard's
  disclosure role is tested even though eligibility is full either way.
- The reviewer's `mt1` is pinned in both halves: `mt1b-rename-default` reproduces its exact flags
  across the shared helper, and `mt1-rename-detection` covers the index/worktree read, which a
  committed-range scenario cannot reach and which is the state a local gate actually runs in.
- One claim in the review did not reproduce here: finding 7 states that `python -m unittest` with no
  arguments "exits 0 having run zero tests (measured)". On this host both interpreters exit **5**
  with `NO TESTS RAN` (`python3.12 -m unittest; echo $?` → 5, `python3.14 -m unittest; echo $?` → 5).
  The guard is kept anyway, because the zero-test exit status belongs to the runner and not to this
  profile: the focused check must refuse with its own reason and run no command, which is what the
  `t7` mutant is killed on.
