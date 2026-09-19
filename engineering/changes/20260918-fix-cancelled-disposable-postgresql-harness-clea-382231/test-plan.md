# Test plan — Fix cancelled disposable PostgreSQL harness cleanup, orphan recovery, and timeout reporting (#128)

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | SIGTERM/SIGINT cancellation stops and reaps descendants before exact container+volume cleanup | Subprocess regression with fake Docker and blocking child |
| P0 | Startup reclaims only verified old owned resources; fresh/foreign/ambiguous resources survive | Table-driven mocked Docker inspect/list/remove tests |
| P0 | More labelled/stale rows than the per-run reclaim bound are reported as backlog while the oldest safe candidates are processed; listing overflow is not a generic harness failure | Backlog regression in `factory/tests/test_migrations.py` |
| P0 | A reclaimed stale container bundle consumes the same single candidate allowance as detached stale volumes; no second category can exceed the per-run bound | `test_exit_runner_shares_reclaim_candidate_budget_across_resource_types` |
| P0 | Inner and outer timeouts report phase+elapsed+budget, remain failing, and differ from assertion failure | Unit tests for timeout and CalledProcessError branches |
| P1 | Partial volume creation and failed container creation still clean or become recoverable | Harness orchestration mocks |
| P1 | Incomplete exact cleanup forces a failing result, and PASS is emitted only after cleanup | Harness orchestration mock verifies resource identities and outcome |
| P1 | Repository-sandbox skip remains explicit and unchanged | Verification summary test |
| P0 | Generic command timeout terminates a descendant that ignores SIGTERM before returning exit 124 | `test_util_run_timeout_terminates_descendants_before_return` |
| P0 | Delayed exact name visibility retries within the deadline and removes only the fully bound ID and volume | `test_exit_runner_retries_delayed_name_visibility_then_removes_exact_bindings` |
| P1 | Container listing stops at row and byte caps, reports backlog, and kills an output-flooding listing process | `test_exit_runner_caps_container_reaper_bytes_and_rows`; `test_docker_bounded_listing_stops_at_output_limit` |
| P1 | Byte overflow is distinct from command failure; incomplete container/volume snapshots report backlog and are skipped | `test_exit_runner_reports_container_list_overflow_as_backlog_and_continues` |
| P1 | KeyboardInterrupt terminates and reaps generic command and bounded Docker listing groups before re-raising | `test_util_run_keyboard_interrupt_stops_descendants_before_reraising`; `test_bounded_docker_listing_keyboard_interrupt_stops_process_group` |
| P1 | Nested Trust CLI removes the outer worker's private child marker and retains inherited xdist tool paths after Trust imports | `test_trust_cli_uses_own_imports_and_keeps_each_file_on_one_worker` |

## Automated checks

- Unit: factory.tests.test_migrations focused runner tests.
- Integration: disposable PostgreSQL exit check and bounded subprocess cancellation test.
- Contract: no public API/schema changes.
- E2E: python3 scripts/grok_verify.py --mode pr.
- Static analysis: Ruff and Bandit selected by route.

## Manual checks

- Verify no labelled disposable resources remain after normal or handled-cancellation test.
