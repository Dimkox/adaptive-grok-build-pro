# AI architecture analysis — issue #129

## Finding

`adaptive_grok.util.run()` is a shared subprocess boundary. Its callers include generic Git/ref discovery and fingerprint helpers in `util.py`, toolchain version detection and dependency installation in `toolchain.py`, architecture tooling in `architecture.py`, and the verification pipeline in `verification.py`. It returns `CompletedProcess[str]` and currently asks `subprocess.run(text=True)` to decode using the process locale/default text encoding with strict error handling.

Changing this shared helper to replacement decoding would prevent decode failures for arbitrary subprocess output, but would silently rewrite invalid byte sequences as U+FFFD for every consumer. For most human-facing diagnostics that may be acceptable, yet some callers consume stdout as identifiers or structured values (for example Git refs, SHAs, version strings, or config values); replacement characters can turn a malformed response into a different string that is still processed downstream. It would also change semantics beyond the whitespace diagnostic that triggered #129.

The diff checker only needs robust presentation of stdout/stderr from `git diff --check`, while its actual pass/fail decision is the subprocess return code. Prefer binary capture plus UTF-8 replacement decoding scoped to `_git_diff_check` (or an equally narrow helper used only there), preserving raw/faithful diagnostics as far as valid UTF-8 allows and keeping `util.run`'s strict/general contract unchanged. Make the failure summary retain command and exit status even if stream decoding is lossy.

## Behavior risks and acceptance details

- Ensure replacement applies to both captured stdout and stderr; Git can emit filenames that are not valid UTF-8 under the active locale.
- Decode only for display. Never base check status, selected refs, or parsed machine values on replacement-decoded diagnostic text.
- Preserve timeout and missing-executable behavior, including return codes 124/127 and usable partial timeout output; subprocess timeout output can be bytes even when text mode was requested, so normalize that explicitly in the local helper.
- Do not broaden `util.run`'s return type or alter its callers unless a repository-wide byte-safe contract is separately designed and tested.
- Tests should exercise invalid UTF-8 in both streams for the diff check, with a nonzero command exit preserved as failure, and should establish that generic `run()` callers retain their existing contract.
