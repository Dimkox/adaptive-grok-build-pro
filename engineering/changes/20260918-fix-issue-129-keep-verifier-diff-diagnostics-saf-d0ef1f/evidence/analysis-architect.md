# Architect analysis: issue #129

## Finding

`verification._git_diff_check()` invokes `util.run()` for worktree, index, and selected PR/release range checks. The command's exit status is the gate; stdout/stderr are diagnostics copied into the `CheckResult`. `util.run()` currently uses `subprocess.run(text=True, capture_output=True)` without an explicit decoding error strategy (lines 76–100). A Git diagnostic containing a filename with undecodable bytes can therefore raise `UnicodeDecodeError` during subprocess result decoding, before `_git_diff_check()` can record a failed check and before the verifier reaches unit tests. The helper is also used by command outputs that callers parse (not only human diagnostics), including refs and configuration checks, so changing all decoded output indiscriminately deserves compatibility scrutiny.

This boundary is repository-local verification. It must preserve the `git diff --check` return code and must not treat replacement text as evidence that the diff passed. The check already gates on each command's return code and can continue to attach textual, bounded output to the report. Git paths are byte sequences; if a display cannot decode them, diagnostics may be lossy but must remain safe and auditable as text.

## Minimal design recommendation

Prefer a narrowly scoped diagnostic-safe execution path for `_git_diff_check()` rather than changing the default contract of `util.run()` for every caller. Either add an explicit decoding-errors option to `util.run()` (default unchanged) and pass `errors='backslashreplace'` for these diagnostic-only invocations, including normal and timeout output normalization; or capture bytes in this check and render with `os.fsdecode`/UTF-8 `backslashreplace` before building `CheckResult`. The former is a small reusable seam, while the latter has the smallest behavioral scope. Whichever is chosen, ensure `TimeoutExpired.stdout/stderr` bytes are normalized too: the existing timeout handler returns `exc.stdout` and `exc.stderr` directly, which can violate the declared `CompletedProcess[str]` contract when capture was interrupted.

Do not use `errors='ignore'`: it erases the problematic evidence. `backslashreplace` keeps offending byte values visible (for example `\xff`) without embedding surrogate code points that can break JSON/report serialization. Keep the original subprocess return code authoritative, keep stdout/stderr bounds already applied by `_git_diff_check()`, and do not relax selection findings or fail-closed behavior.

## Callers and risks

- `util.run()` is shared across verification, range discovery, and other modules; adding a default tolerant policy can silently alter strings consumed by parsers. A strict default plus opt-in tolerant diagnostics minimizes that risk.
- If the implementation instead makes `run()` globally tolerant, inspect every caller that parses stdout and confirm malformed/replaced output still fails closed. In particular, commit/object IDs and structured values must not accept replacement characters.
- `find_root()` has a separate direct `subprocess.run(text=True)` call, but it is not on the `git diff --check` path described by #129.
- Preserve a regression where an invalid-UTF8 filename produces a nonzero diff-check result and a serializable report, without aborting the verifier. Also cover clean output and timeout normalization if the shared helper is modified.

No product files were changed during this read-only analysis.
