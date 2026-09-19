# Repository analysis — issue #129

## Finding

`git diff --check` is called by `adaptive_grok.verification._git_diff_check()` in `.grok-stack/adaptive_grok/verification.py` (around lines 596–627). It executes three possible classes of commands: working tree, index, and (for PR/release mode) selected `<base>..HEAD` ranges. It records each subprocess `stdout`/`stderr` in the corresponding `CheckResult` and adds `diff-check-failed` details for nonzero exits.

All these calls use `adaptive_grok.util.run()` (`.grok-stack/adaptive_grok/util.py`, around lines 76–99). That helper calls `subprocess.run(..., text=True, capture_output=True)` without an explicit decoding policy. Python therefore strictly decodes the captured output using the locale encoding. A filename containing invalid bytes can make Git print undecodable bytes in a whitespace diagnostic, causing `UnicodeDecodeError` inside `subprocess.run`; `util.run()` catches only `FileNotFoundError` and `TimeoutExpired`, so this escapes `_git_diff_check()` and aborts verification before its check result is returned.

The fix should preserve output in a safe, loss-tolerant representation and keep the command's exit code and check classification authoritative. A narrowly scoped decode policy for captured subprocess text (e.g. UTF-8 with replacement, or decoding Git's bytes for this check) avoids a crash while making undecodable bytes visible as replacement markers. Do not suppress the failed command, discard its status, or turn malformed path bytes into silently normalized text.

## Existing regression-test location and setup

`tests/test_verification_doctor.py` contains the appropriate focused integration coverage:

- `_divergent_pr_graph()` creates a temporary Git project and selected PR base/target refs.
- `VerificationDoctorTests.test_pr_git_diff_check_rejects_whitespace_only_visible_from_local_target` (around line 319) exercises an actual range `git diff --check` and asserts the `git-diff-check` result and diagnostic.
- Neighboring cases cover clean committed ranges, staged whitespace, invalid bases, ambiguous targets, and multiple merge bases.

Add a sibling test in that group. Create a tracked file whose name contains a byte not valid UTF-8 (use filesystem byte APIs such as `os.fsencode`/`os.fsdecode` with surrogateescape, or a bytes path passed to filesystem APIs), commit it with a trailing-space line, and ensure the working diff or selected committed range makes `git diff --check` emit the undecodable path byte. Then call `verify(..., mode='pr', record=False)` with git-only command detection as the neighboring test does. Assert verification returns a `git-diff-check` result instead of raising; assert the whitespace defect remains a `fail` and the diagnostic safely indicates the undecodable byte (replacement or documented escaped representation). Keep the test portable by checking the diagnostic representation contract rather than the locale-specific rendered character, and use a filename byte that is invalid under UTF-8.

A lower-level utility test could independently pin tolerant decoding, but the end-to-end verification regression is essential because the reported failure is an escaping exception before a check result. Avoid tests that depend on the host locale; the defect is triggered by invalid UTF-8 bytes irrespective of locale when the locale decoder is UTF-8.

## Scope observations

The failure comes from the shared `util.run()` API, not a test runner invocation. `verification.py` also uses `run()` for Git range discovery, hooks, package manager commands, and PHP lint. A shared decode policy would make these calls resilient too; assess callers for any expectation that subprocess output must be lossless. `util.run()` returns `CompletedProcess[str]` and currently has no `encoding`/`errors` override. The public check result already stores human-readable `stdout`/`stderr`, so a safe text representation fits its current contract.

No source or test changes were made during this analysis.
