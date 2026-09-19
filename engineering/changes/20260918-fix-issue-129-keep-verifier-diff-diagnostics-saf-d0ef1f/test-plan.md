# Test plan — Fix issue #129: keep verifier diff diagnostics safe for non-UTF-8 repository paths

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | A real temporary Git repository contains a tracked filename with an invalid UTF-8 byte and trailing whitespace; `_git_diff_check` returns a failed result instead of raising | `VerificationTests.test_diff_check_keeps_non_utf8_filename_failure_serializable` |
| P0 | CheckResult diagnostic is valid Unicode/JSON, shows a replacement or escaped marker, and retains the nonzero diff-check finding | Same end-to-end regression and report serialization assertion |
| P1 | Ordinary UTF-8 diagnostics and the default `util.run()` behavior stay unchanged; missing-command and timeout behavior remain compatible | focused unit/integration tests for `util.run` and diff-check |

## Automated checks

- Unit: `VerificationTests.test_run_decode_opt_in_preserves_strict_default_and_timeout_contract`.
- Integration: real invalid-byte repository path exercised through `_git_diff_check()`.
- Contract:
- E2E:
- Static analysis:

## Manual checks

- Confirm tests skip with an explicit reason only on platforms/filesystems that cannot create byte-distinct invalid UTF-8 paths.

## Executed checks

- Red baseline: `python3 -m unittest tests.test_verification_doctor.VerificationTests.test_diff_check_keeps_non_utf8_filename_failure_serializable` failed with `UnicodeDecodeError` on byte `0xff`.
- Green regressions: `python3 -m unittest tests.test_verification_doctor.VerificationTests.test_diff_check_keeps_non_utf8_filename_failure_serializable tests.test_verification_doctor.VerificationTests.test_run_decode_opt_in_preserves_strict_default_and_timeout_contract` — 2 passed.
- Existing diff-check regressions: four selected worktree/range/whitespace tests — 4 passed.
- `git diff --check` — passed.
