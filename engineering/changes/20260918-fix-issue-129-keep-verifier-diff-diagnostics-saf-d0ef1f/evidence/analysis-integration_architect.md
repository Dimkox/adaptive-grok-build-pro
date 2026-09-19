# Integration analysis — issue #129

## Existing boundary

`verification._git_diff_check()` invokes `git diff --check` for the worktree, index, and selected PR/release ranges. Each invocation goes through the shared `util.run()` helper. That helper calls `subprocess.run(..., text=True, capture_output=True)` without setting an encoding or decoding error policy, then normalizes missing executables and timeouts into a `CompletedProcess[str]`. Python's locale-selected text decoder can therefore raise `UnicodeDecodeError` while `git diff --check` is returning diagnostics for a repository path whose bytes are not valid in that encoding. The error happens before `_git_diff_check()` can aggregate results into its normal check record.

The check already keeps stdout and stderr separate, collects output from all ranges, retains the exit code in error details, and reports total passed checks plus the selected bases. `CheckResult.to_dict()` uses dataclass serialization; downstream `grok_verify.py` and the report JSON expect ordinary strings. Preserve these interfaces and the current failure semantics.

## Subprocess behavior to preserve

- **Normal exit 0:** decoded stdout/stderr remain attached to their respective report fields, and that invocation counts as passed.
- **Normal nonzero exit:** collect both streams, increment failed invocation count, append the existing `diff-check-failed` detail with the exact exit code and command, and continue running the remaining checks. Diagnostics alone do not decide pass/fail; Git's return code does.
- **Timeout:** `run()` currently maps `TimeoutExpired` to return code 124 and provides captured streams or a timeout fallback. The diff checker treats this as an ordinary failed invocation and aggregates it with other failures. Keep timeout behavior intact and ensure partial output remains serializable if the underlying decoder policy changes.
- **Missing Git:** `command_exists('git')` yields skip before invocation. Preserve.
- **Range-selection findings:** these are already fail-closed and remain in details independently of invocation outcomes.

## Recommended scope

Use a narrow, explicit decoding policy for subprocess text produced by the diff diagnostics (prefer UTF-8 with `errors='replace'`, or a deliberate filesystem-aware decoding strategy), such that invalid bytes cannot escape as `UnicodeDecodeError`. Keep the public `run()` return contract as strings and do not broaden changes to unrelated Git metadata, tools, or subprocess callers unless the root cause proves the helper itself must gain an opt-in mode. Do not alter check aggregation, commands, selected bases, check statuses, exit-code handling, output truncation, report schema, or receipt identity.

Tests should use a real temporary Git repository and a POSIX filename containing bytes invalid under UTF-8 (where supported), create trailing whitespace so `git diff --check` emits a path-bearing diagnostic, then call verification. Assert verification returns a report instead of raising, the diff check fails because Git returned nonzero, its diagnostic remains readable/representable in stdout or stderr and report serialization succeeds. Add a clean-path control (pass), and preserve coverage of staged/worktree/committed ranges and multi-check aggregation. If the project runs on platforms that cannot create raw-byte filenames, skip that focused case based on capability rather than weakening the assertion.

## Out of scope

No path canonicalization or renaming; no claim that a replacement-decoded display path is a reversible representation of the original Git path bytes; no change to diff policy or whitespace rules; no generic subprocess redesign; no binary output in JSON reports; no changes to API contracts, Git hosting integrations, Trust CI, or release behavior.
