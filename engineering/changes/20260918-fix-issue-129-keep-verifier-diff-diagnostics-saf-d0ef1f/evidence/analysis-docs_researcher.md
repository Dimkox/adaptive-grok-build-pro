# Documentation and compatibility analysis — issue #129

## Findings

`adaptive_grok.util.run()` is a shared helper, not a Git-only wrapper. It currently returns `CompletedProcess[str]` via `subprocess.run(..., text=True, capture_output=True)` and catches missing-command and timeout conditions. Its callers include Git range/base selection, changed-file/fingerprint discovery, architecture checks, configured verification commands and toolchain scripts. Changing the shared decoder therefore changes behavior across unrelated verification and could silently turn invalid output into replacement characters everywhere.

`verification._git_diff_check()` runs only Git's `diff --check` variants (worktree, index and selected PR/release ranges). It forwards stdout/stderr into the typed `CheckResult` string fields, clips the rendered result to 12,000 characters, and records nonzero exit status as a finding. The product contract is that this diagnostic must not abort verification and that the command's exit status and human-readable evidence remain visible. No repository contract requires strict UTF-8 for Git diagnostic text.

There is an existing local precedent for best-effort diagnostic decoding: `python_test_runner.py` decodes bounded subprocess streams with UTF-8 `errors='replace'`, and `util.read_text_limited()` does the same for diagnostic/read-only text. In contrast, structured repository files and architecture/schema loaders use strict UTF-8 and report malformed input as invalid data. These are appropriately different semantics: diagnostics should survive undecodable bytes, while machine-readable inputs should fail validation.

## Recommendation

Prefer diff-check-specific decoding at the `util.run()` boundary only if that boundary can be explicitly opted into (for example, a narrowly named decoding policy/flag defaulting to current strict text behavior); otherwise capture this Git invocation in bytes and decode stdout/stderr with UTF-8 `errors='replace'` inside `_git_diff_check()`. Do not globally change `util.run()` to `errors='replace'`: that helper has many unrelated callers, and tolerant decoding there would suppress evidence of malformed output in checks that may rely on strict decoding.

The user-visible semantics should remain: return a normal `git-diff-check` fail result when Git exits nonzero, retain all decodable text, replace only invalid byte sequences with U+FFFD in the diagnostic fields, and continue running the remaining diff-check commands. Encoding damage must not change the process exit code, check count, failure count, or selection findings. Keep the result bounded using the existing output limit.

`surrogateescape` can preserve the original byte values through a Python string round trip, but `CheckResult` is subsequently serialized to JSON and rendered for operators; lone surrogate code points can be rejected or rendered inconsistently by downstream UTF-8 writers. For this user-facing diagnostic record, replacement decoding is safer than surrogate preservation. If exact raw-byte forensics ever becomes a requirement, add an explicit bounded base64/hex field with a versioned contract instead of placing surrogates in ordinary text.

## Compatibility and focused coverage implications

- Preserve `util.run()`'s existing default behavior for all current consumers and its `CompletedProcess[str]` contract.
- Exercise invalid bytes independently in stdout and stderr for the diff-check command; assert the verifier completes, stores a valid Unicode `CheckResult`, preserves the nonzero exit failure, and still runs later checks.
- Keep ordinary UTF-8 output byte-for-byte unchanged, and retain existing timeout/missing-git behavior.
- Do not alter parsing of Git paths or structured contracts; this issue concerns diagnostics emitted by `git diff --check`, not Git's path protocol.
