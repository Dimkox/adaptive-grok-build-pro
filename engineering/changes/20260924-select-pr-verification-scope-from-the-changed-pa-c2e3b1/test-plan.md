# Test plan — Select PR verification scope from the changed-path inventory (issue 205)

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | A release documentation/state inventory (the v2.0.19 release-sync shape: prose, `PROJECT_STATE.json`, `VERSION`, tracked `packages/**`, admitted modules) selects `docs-state-focused`, and full discovery plus coverage measurement do not run | `tests.test_verification_scope.DocsStateScopeSelectionTests.test_release_sync_inventory_selects_the_focused_profile`; `FocusedPythonExecutionTests.test_admitted_inventory_never_executes_full_suite_discovery`; `VerifyDocsStateScopeEndToEndTests.test_verify_selects_and_runs_the_focused_profile_for_a_docs_only_successor` |
| P0 | Adding one executed-behavior path to the same inventory puts the full suite back, and the report says which path | `DocsStateScopeSelectionTests.test_every_executable_or_contract_bearing_path_keeps_the_full_profile` (37 paths, one per subTest); `FocusedPythonExecutionTests.test_mutating_one_source_path_flips_the_same_tree_to_full_discovery`; `VerifyDocsStateScopeEndToEndTests.test_verify_puts_the_full_suite_back_for_one_committed_source_change` |
| P0 | Shipped-and-executed content is refused: editing `docs/bitrix-local-AGENTS.md` cannot ride a prose lane, because `scripts/install_into.py` installs it verbatim as `local/AGENTS.md` into every consumer Bitrix install | `RoleBasedAdmissionTests.test_shipped_and_executed_content_is_rejected_by_its_own_reason_code`; `FULL_PATH_ONLY_CHANGES` |
| P0 | Declared-immutable evidence is refused: `engineering/changes/*/evidence/historical-*` bytes are sha256-pinned by `tests/test_history.py` (verified: exactly those two files carry a literal pin; the structural rule also covers the third `historical-shared-handoffs.json` and any future bundle) | `RoleBasedAdmissionTests.test_declared_immutable_historical_evidence_is_rejected_by_its_own_reason_code`; `test_a_sibling_of_an_admitted_evidence_name_stays_admitted_by_prefix` (the refusal is narrow, not a directory veto) |
| P0 | A source path cannot be removed behind a documentation name, even when the primary inventory is rename-collapsed to one admitted path | `RealRepositoryInventoryTests.test_a_source_path_removed_behind_a_docs_name_never_selects_it`; `DocsStateStatusInventoryTests.test_a_rename_blind_primary_inventory_still_meets_the_status_veto` |
| P0 | A change to the classifier, the verifier, the shared Git plumbing or the CLI can never be certified by the lane it just changed | `DocsStateScopeSelectionTests.test_the_shortcut_selectors_own_module_cannot_be_edited_in_focused_scope`; `RoleBasedAdmissionTests.test_the_lane_tests_themselves_are_not_admitted`; `FULL_PATH_ONLY_CHANGES` |
| P1 | Every admitted content class whose machine binding is a test module is bound by a module this lane runs (`README.md`'s Workflow-sources table by `tests/test_workflow_sources.py`, a delivered package's `route.json` by `tests/test_repo_router.py`) | `DocsStateScopeSelectionTests.test_every_admitted_content_class_is_re_derived_by_a_module_this_lane_runs` (asserts the modules admit it *and* that those test files really read that content) |
| P1 | The status veto channel spans exactly the inventory domain: untracked additions arrive as `'??'` records, and copy detection on a staged successor package cannot push an honest docs change out of the lane | `DocsStateStatusInventoryTests.test_untracked_paths_arrive_as_status_records_so_the_veto_covers_them`; `test_a_staged_successor_package_is_not_pushed_out_by_copy_detection`; `test_the_shared_helper_still_reports_renames_and_copies_by_default` |
| P1 | Prefix matching cannot be escaped by a name collision or by an unnormalized path | `RoleBasedAdmissionTests.test_a_suffix_glued_sibling_of_an_admitted_log_is_not_admitted`; `test_an_unnormalized_path_cannot_escape_the_prefix_rules`; `test_documentation_prefixes_are_directory_shaped_only`; `test_an_undeclared_name_under_an_admitted_directory_is_not_admitted` |
| P1 | The disclosure is complete and the focused runner cannot go green on zero tests | `DocsStateScopeCheckRenderingTests.test_eligible_check_names_every_admitted_path_and_each_skip`; `FocusedPythonEmptyTargetTests.test_an_empty_target_list_fails_instead_of_reporting_a_green_zero_test_run`; `test_the_replaced_runner_is_named_by_the_caller_not_assumed` |
| P1 | Every fail-closed veto still fires: absent route, untrusted or missing status inventory, empty/ambiguous/unbased range, operator override, absent admitted module | `DocsStateScopeSelectionTests.test_missing_or_untrusted_status_inventory_fails_closed`, `test_empty_ambiguous_or_unbased_inventories_keep_the_full_profile`, `test_operator_override_defeats_the_shortcut`, `test_an_absent_lockstep_target_cannot_be_run_by_the_focused_profile`; `VerifyDocsStateScopeEndToEndTests.test_verify_refuses_the_lane_when_the_status_channel_is_not_trusted`, `test_verify_refuses_the_lane_when_an_admitted_module_is_absent_from_the_checkout` |
| P2 | The landing focused contract is untouched by the shared `changed_file_statuses` helper and by `--mode pr` | `tests.test_verification_doctor` (85 tests, `Ran 85 tests in 222 s` on this checkout); `DocsStateScopeSelectionTests.test_fast_and_landing_modes_are_not_gated_scopes` |

## Automated checks

- Unit: `python3 -m unittest tests.test_verification_scope -q` → `Ran 47 tests ... OK` (8.7 s). Covers
  the pure classifier, admission roles and reason codes, check rendering, `_python`/`_focused_python`
  execution, the status side channel on real temporary repositories, and four `verify()` end-to-end
  arms on a temporary git repository whose route base is the parent commit.
- Focused-lane cost (what the profile itself runs, measured in this repository):
  `python3 -m unittest tests.test_structure tests.test_project_state tests.test_manifest_package tests.test_workflow_sources tests.test_repo_router -q`
  → 14.0 s against the 629 s serial coverage run it replaces.
- Contract: the same five admitted modules are the contract re-derivation for root identity, dated
  state, package bytes, README's Workflow-sources table, and a delivered change package's route
  record; `tests.test_change_spec` and `tests.test_receipts` keep receipt semantics unchanged.
- Integration: `python3 -m unittest tests.test_verification_doctor tests.test_util_fingerprint tests.test_repo_router tests.test_history -q`
  — the landing lane shares `util.changed_file_statuses`, and the default `rename_detection=True`
  must stay byte-identical for it.
- E2E: one authoritative `python3 scripts/grok_verify.py --mode pr` on the final tree; its verdict
  and the `docs_state_scope` block are stored in the fingerprint-bound receipt for that tree.
- Static analysis: `python3 -m ruff check .grok-stack/adaptive_grok scripts tests`; bandit per
  `bandit.yaml`; `git diff --check origin/main..HEAD` clean over the whole delivered range
  (change-package scaffolds ship with trailing whitespace, so package files are stripped before
  verification).
- Mutation proof: 20 mutants applied to a scratch copy outside the worktree, each run against
  `tests.test_verification_scope`. Control (unmutated copy): `Ran 47 tests ... OK`. Result: 20
  killed, 0 survived — including the four the review of head `a08060c1` listed as surviving
  (`mw1`, `mw2`, `mw3`, `mp1`) and both re-widened admission mutants (`docs/` wholesale,
  historical evidence). Full table:
  [`evidence/mutation-battery-205.md`](evidence/mutation-battery-205.md).

## Manual checks

- Read one focused receipt and confirm `docs_state_scope.skipped_checks` names the replaced
  discovery runner, `coverage` and `factory-postgres-exit`, and that no skipped check is recorded
  as passed.
- Confirm the printed `docs-state-scope` summary (`profile=`, `evidence=`, `reason=`, `paths=`,
  `skipped=`) agrees with the changed-file inventory printed in the same run.
- Confirm README.md and AGENTS.md describe the implemented role rule — named documentation files,
  directory-shaped prefixes only, `shipped-executed-content` and `immutable-historical-evidence`
  refusals, five admitted modules, three declared skips — with no leftover claim that `docs/`
  rides the lane as a directory or that only two checks are skipped.
