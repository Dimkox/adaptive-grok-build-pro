# M1 security re-review 6

## Verdict

**PASS** for exact HEAD `9a6e27c193ec944a149e452ff7591fbc7493238c` against prior reviewed HEAD `25b9562144c774e125851019c02de6eca7a4a828`.

Both blockers from `review-security_reviewer-5.md` are closed. The remediation isolates all trusted-host Git configuration from the checkout and reliably terminates the original process group, including SIGTERM-ignoring descendants after the leader exits. No new blocking security or correctness finding was identified in the remediation diff or surrounding M1 trust boundaries.

## Exact-HEAD evidence

- Initial repository identity: `git rev-parse HEAD` returned `9a6e27c193ec944a149e452ff7591fbc7493238c`; `git status --short` was clean.
- Focused Trust CI security suites (`test_workspace`, `test_policy`, `test_runner`, holdout, signing, PostgreSQL) — **95 total, 85 passed, 10 skipped**. Skips are the disclosed conditional PostgreSQL tests because `TRUST_CI_TEST_DATABASE_URL` is not configured.
- Full root discovery — **223 passed**.
- Full Trust CI discovery — **195 total, 185 passed, 10 skipped**.
- `git diff --check 25b9562144c774e125851019c02de6eca7a4a828..HEAD` — passed.
- Holdout bundle remained exactly the two checked-in files `change_spec_validate.py` and `validate.py` after testing.

## Review-5 closure

### SEC-R5-001 — closed: checkout-owned Git configuration cannot influence trusted commands

- `GitWorkspace.__init__()` creates a private mode-0700 configuration home beside, not inside, the checkout, with a separate XDG directory; partial checkout creation is cleaned on initialization failure (`trust-ci/src/adaptive_trust_ci/workspace.py:217-236`).
- `_git_env()` points `HOME` and `XDG_CONFIG_HOME` at that trusted directory, explicitly disables global/system Git configuration, disables system attributes, and injects command-scope `core.hooksPath=/dev/null` plus `core.fsmonitor=false` (`workspace.py:399-425`). The authenticated HTTP header is added only for authenticated fetch calls.
- `cleanup()` removes both checkout and trusted configuration home (`workspace.py:345-347`).
- `test_git_commands_ignore_committed_executable_global_config` commits a root `.gitconfig` containing fsmonitor, hooks, and external-diff commands, then exercises exact diff, reset, and status. No marker executes; LF path identity and authenticated configuration remain correct; cleanup removes the trusted home (`trust-ci/tests/test_workspace.py:122-176`).

The repository-controlled root `.gitconfig` is therefore data inside the checkout, not a Git configuration source for the privileged host process.

### SEC-R5-002 — closed: the original process group is terminated and the leader reaped

- The process-group ID is captured immediately from the new-session leader and passed independently through all error cleanup (`workspace.py:130-154,196-199`).
- `_signal_process_group()` and `_process_group_exists()` refuse the worker's own group, tolerate ESRCH races, and fail closed on inspection errors (`workspace.py:72-96`).
- `_terminate_process()` applies SIGTERM to the original group, polls group existence while reaping the leader, escalates surviving members to SIGKILL after the bounded grace interval, verifies group disappearance, and separately verifies direct-leader reaping (`workspace.py:99-128`).
- `test_bounded_process_kills_sigterm_ignoring_descendants` covers stdout overflow, stderr overflow, and timeout with a promptly exiting leader plus a same-group descendant that ignores SIGTERM. Each case returns only after the descendant is gone (`trust-ci/tests/test_workspace.py:274-308`). Own-group refusal and nonexistent-group races are separately covered at lines 310-315.

## Surrounding boundary regression review

- Exact `.grok-stack/**`, `.grok/**`, `.github/**`, `.coveragerc`, literal-backslash, Unicode, LF, and tab approval-scope matching remains intact; action-required and valid signed-approval runner tests pass.
- Git diff/status output remains incrementally bounded by aggregate bytes, record bytes, record count, stdout, stderr, and timeout. Invalid UTF-8, unsafe paths, malformed NUL records, unavailable exact SHAs, and over-limit inputs remain fail-closed.
- Local/holdout/trusted parser agreement remains intact for nested validation, unpaired surrogates, malformed JSON, controls, recursion, and contract paths.
- Descriptor-relative no-follow reads, ancestor-symlink rejection, raw/semantic spec provenance, spec-local criterion IDs, signed zero-coverage failure, tamper detection, and public-only pre-M1 golden replay remain covered and passing.
- PostgreSQL legacy/current round-trip tests remain present but were not executed without the configured test database; no database-backed claim is made by this report.

## Security conclusion

The reviewed source is locally security-review ready at exact HEAD `9a6e27c193ec944a149e452ff7591fbc7493238c`. This report is repository-local preflight evidence only: it does not deploy the holdout/worker/policy, create a human approval, or substitute for the App-owned policy-epoch exact-SHA Trust CI check and required external signed approvals.
