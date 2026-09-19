# Initial implementation evidence — #128 (before data-review follow-up)

Route `3822310b0593`; worktree `fix/issue-128-disposable-cleanup`.

## Targeted checks on the current implementation

- `ruff check .grok-stack/adaptive_grok/python_test_runner.py .grok-stack/adaptive_grok/util.py .grok-stack/adaptive_grok/verification.py factory/tests/run_disposable_exit.py factory/tests/test_migrations.py tests/test_python_test_runner.py tests/test_verification_doctor.py` — pass.
- Explicit `python3 -m unittest -v` selections — 22 passed in 9.811s:
  - `factory.tests.test_migrations.MigrationTests.test_exit_runner_orders_bound_preflight_before_mutating_suite`
  - `factory.tests.test_migrations.MigrationTests.test_exit_runner_removes_only_fully_bound_container_and_volume`
  - `factory.tests.test_migrations.MigrationTests.test_exit_runner_retries_delayed_name_visibility_then_removes_exact_bindings`
  - `factory.tests.test_migrations.MigrationTests.test_exit_runner_caps_container_reaper_bytes_and_rows`
  - `factory.tests.test_migrations.MigrationTests.test_docker_bounded_listing_stops_at_output_limit`
  - `factory.tests.test_migrations.MigrationTests.test_exit_runner_reports_container_list_overflow_as_backlog_and_continues`
  - `factory.tests.test_migrations.MigrationTests.test_bounded_docker_listing_keyboard_interrupt_stops_process_group`
  - `factory.tests.test_migrations.MigrationTests.test_bounded_docker_listing_interrupt_during_selector_setup_stops_process_group`
  - `factory.tests.test_migrations.MigrationTests.test_exit_runner_parses_timezone_offset_and_reclaims_verified_stale_container`
  - `factory.tests.test_migrations.MigrationTests.test_exit_runner_reaper_preserves_stale_row_when_exact_binding_fails`
  - `factory.tests.test_migrations.MigrationTests.test_exit_runner_reports_reaper_backlog_and_processes_only_one_candidate`
  - `factory.tests.test_migrations.MigrationTests.test_exit_runner_partial_create_is_unwound_and_exact_volume_mount_is_used`
  - `tests.test_verification_doctor.VerificationTests.test_util_run_keyboard_interrupt_stops_descendants_before_reraising`
  - `tests.test_verification_doctor.VerificationTests.test_util_run_timeout_terminates_descendants_before_return`
  - `tests.test_verification_doctor.VerificationTests.test_command_check_normalizes_timeout_output_bytes_for_json`
  - `tests.test_verification_doctor.VerificationTests.test_python_pr_skips_factory_postgres_exit_only_in_repository_sandbox`
  - `tests.test_verification_doctor.VerificationTests.test_python_pr_propagates_local_factory_postgres_exit_failure`
  - `tests.test_verification_doctor.VerificationTests.test_factory_postgres_exit_timeout_is_distinct_from_command_failure`
  - `tests.test_verification_doctor.VerificationTests.test_factory_postgres_exit_cancellation_waits_for_harness_unwind`
  - `tests.test_verification_doctor.VerificationTests.test_factory_postgres_exit_escalates_and_reaps_unresponsive_harness`
  - `tests.test_verification_doctor.VerificationTests.test_harness_run_stops_child_group_before_cleanup_unwinds`
  - `tests.test_python_test_runner.PythonTestRunnerTests.test_trust_cli_uses_own_imports_and_keeps_each_file_on_one_worker`
- `python3 scripts/grok_spec.py validate --change-id 20260918-fix-cancelled-disposable-postgresql-harness-clea-382231 --gate` — pass; 8/8 acceptance criteria mapped, no errors.
- `python3 -m py_compile` on the seven changed Python files — pass.
- `git diff --check` — pass.

Ruff first reported an unused local and an assigned lambda in the modified migration test module; both were corrected, then Ruff and all 22 selected regressions were rerun successfully.

The repository-wide `python3 scripts/grok_verify.py --mode pr` quality profile is intentionally not claimed here; the coordinator is serializing that full verifier. No live Docker/PostgreSQL integration run was performed. Independent reviews and fingerprint-bound receipts remain pending coordinator action.

## Data-review follow-up

The data review identified that the former 70-second outer TERM grace did not cover the harness's bounded process-stop plus exact resource cleanup path, and that the one-candidate cap had been applied independently to container and volume sweeps. The follow-up changes raise TERM grace to 101 seconds and cleanup reserve to 110 seconds within the unchanged 600-second cap; a regression conservatively derives a 100-second harness unwind bound and asserts strict headroom. With the 490-second work window, 101-second TERM grace, 2-second escalation grace, 5-second forced-reap allowance, and 0.05-second poll interval, the modeled total is 598.05 seconds. The reaper shares one remaining candidate allowance across stale container bundles and detached volumes; the typed AC explicitly defines that contract.

Follow-up validation passed after the serialized #104 verifier exited:

- `python3 -m unittest -v` with these six focused regressions — 6 passed in 0.616s:
  - `factory.tests.test_migrations.MigrationTests.test_exit_runner_shares_reclaim_candidate_budget_across_resource_types`
  - `factory.tests.test_migrations.MigrationTests.test_exit_runner_reports_reaper_backlog_and_processes_only_one_candidate`
  - `tests.test_verification_doctor.VerificationTests.test_factory_exit_term_window_covers_harness_cleanup_within_outer_cap`
  - `tests.test_verification_doctor.VerificationTests.test_factory_postgres_exit_waits_for_delayed_cleanup_before_escalation`
  - `tests.test_verification_doctor.VerificationTests.test_factory_postgres_exit_cancellation_waits_for_harness_unwind`
  - `tests.test_verification_doctor.VerificationTests.test_factory_postgres_exit_escalates_and_reaps_unresponsive_harness`
- Ruff passed on the four changed Python files; `py_compile`, change-spec gate validation (8/8 AC mapped), and `git diff --check` passed.

The final strict-headroom adjustment was then checked with these focused regressions — 2 passed in 0.304s:

- `tests.test_verification_doctor.VerificationTests.test_factory_exit_term_window_covers_harness_cleanup_within_outer_cap`
- `tests.test_verification_doctor.VerificationTests.test_factory_postgres_exit_waits_for_delayed_cleanup_before_escalation`

Ruff and `py_compile` passed on the two changed Python files, and `git diff --check` passed.
