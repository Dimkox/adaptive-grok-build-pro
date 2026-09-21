# Docs and acceptance analysis — issue #168

Source: `evidence/source-issues.json` in this change. This is read-only analysis, not a fresh reproduction or verification receipt.

## Acceptance and meaningful regression checks

- Create a temporary Git consumer with a committed base, record `tree_fingerprint()`, create and edit an **untracked** `.qwen/tmp/probe` file, and assert the fingerprint stays fixed. Remove it and assert it remains fixed. This is the issue's measured A/B; use the source issue's digest only as historical evidence, not an expected value.
- Track a file at the same `.qwen/tmp/` path and edit it: fingerprint must change. Also edit tracked `.qwen/` configuration and untracked `.qwen/config` (outside the narrow scratch subtree): each must change the fingerprint. Repeat equivalent controls for any other scratch prefix added. A normal untracked source file and the current Git HEAD must remain bound.
- Test a failure or timeout from `git ls-files` used to establish the tracked set. It must preserve or increase hashing, never silently exclude a candidate scratch path. Test the no-HEAD/non-Git path so an excluded scratch directory does not turn into a broad agent-root ignore.
- Exercise `changed_files()` separately from `tree_fingerprint()`. The former also feeds verification changed-file selection and route state; a fix that only masks receipt comparison can leave noisy files in a gate or hide meaningful changed files. `tests/test_change_receipts.py` and `tests/test_verification_doctor.py` have receipt/current-fingerprint patterns, but the minimal regression belongs near direct utility tests as well.

## Current source and scope tension

- `.grok-stack/adaptive_grok/util.py:129-201` filters `.grok-stack/runtime/` and common generated files before `changed_files()` includes staged, unstaged, and untracked Git paths. It does **not** exclude `.qwen/tmp/`; `tree_fingerprint()` hashes the resulting path and bytes with HEAD. `.grok-stack/adaptive_grok/receipts.py:702-703` then reports stale evidence on a mismatch. The staleness message is a symptom, not a requirement to expose agent scratch paths in receipts.
- The source issue suggests ignoring whole agent directories or allowing arbitrary ignore configuration. The selected route and parent task narrow this: only generated scratch directories, and only while untracked. `.codex`, `.agents`, `.qwen` configuration and all tracked files remain evidence-bound. A configurable ignore list could hide source and exceeds this route.
- `changed_files()` currently ignores unsuccessful Git subcommands (`proc.returncode != 0`). Any new tracked-set query must fail conservatively; a missing tracked-set result cannot be interpreted as “all files are untracked.” The fallback branch currently walks all files, so it needs equivalent conservative behavior if modified.
- This is local evidence-fingerprint behavior. Source tests can establish fingerprint stability and sensitivity but cannot mint external App-owned Trust CI authority or prove a future receipt is current after subsequent tree edits.

## Documentation/source of truth

The source issue's broad agent-directory examples are a proposed direction, not acceptance authority. `AGENTS.md` requires fingerprints bound to the current repository state and says local receipts are stale after any repository change; excluding only transient untracked scratch is consistent with that purpose. No primary web documentation is needed to interpret the Git commands or repository contract here.
