# Security review — issue #129

**Result: PASS**

Reviewed the current changes in `util.py`, `verification.py`, and `tests/test_verification_doctor.py`, with surrounding subprocess and report serialization paths.

- The changed subprocess call remains an argv list passed to `subprocess.run`; it does not introduce a shell, alter the command, working directory, environment, or 60-second timeout. `git-diff-check` pass/fail continues to depend on the process return code and selection findings, not on successful text decoding.
- UTF-8 with `backslashreplace` is opted into only for the three `git diff --check` commands. Other `util.run()` callers retain the prior strict/default decoding contract. On timeout, byte output is decoded using the selected encoding and error policy; missing-command and timeout return codes remain 127 and 124.
- Undecodable bytes become printable escape sequences such as `\\xff`, so the result is valid Unicode and serializes as JSON. JSON control-character escaping remains provided by `json.dumps`; hostile path text cannot change the command or verification authority. Git diagnostics may still contain valid Unicode formatting characters, which consumers displaying untrusted report strings should treat as untrusted text.
- Output fields in `_git_diff_check` remain truncated to 12,000 characters. The underlying `capture_output=True` still buffers each subprocess stream before this truncation, so peak memory is not bounded by that field limit. This is pre-existing behavior in the shared `run()` helper and was not added by this patch; it remains a hardening opportunity if hostile repositories with very large diagnostic streams are in scope.

No security defect introduced by this change was found. No product files were modified and no full verifier was run.
