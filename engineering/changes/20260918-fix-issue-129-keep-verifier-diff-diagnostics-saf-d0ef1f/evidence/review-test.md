# Test review — issue #129

**Result: PASS**

Reviewed the current diff in `tests/test_verification_doctor.py`, the `util.run()` decoding changes, and `_git_diff_check()` integration against the issue acceptance criteria and test plan.

- `test_diff_check_keeps_non_utf8_filename_failure_serializable` creates an actual POSIX filename containing byte `0xff`, disables Git path quoting to exercise undecodable output, stages a line with trailing whitespace, invokes `_git_diff_check()`, and JSON-serializes the resulting `CheckResult`. It asserts a failed status, a `diff-check-failed` finding with a nonzero exit code, an escaped `\xff` in captured diagnostics, and absence of surrogate escapes in serialized JSON. This exercises the original failure mode end to end, including retention of the diagnostic rather than merely asserting no exception.
- `test_run_decode_opt_in_preserves_strict_default_and_timeout_contract` verifies the default call does not opt into custom encoding/error handling and returns ordinary UTF-8 text; it also verifies byte-valued timeout output is decoded with the explicit policy and that missing-command behavior remains return code 127.
- Ran both new tests directly with `python3 -m unittest ...`; **2/2 passed**. `git diff --check` also passed for the patch.

No test gap found that blocks this change. The non-POSIX skip is appropriate because the regression depends on raw-byte POSIX filenames. Full PR verification is outside this read-only test-review task and remains coordinator-owned.
