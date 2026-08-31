# M1 security re-review 5

## Verdict

**BLOCKED** for exact HEAD `25b9562144c774e125851019c02de6eca7a4a828` (security remediation commit `308822528bc92fd017641af5e20eba231d35ae86`) against prior reviewed HEAD `ee9ed6ada12f78f808a12df311a41d7888ca9d30`.

Both findings from `review-security_reviewer-4.md` are materially repaired: policy globs and changed paths retain exact identity, and Git output/record limits are enforced incrementally rather than after full capture. Two trusted-host process-boundary findings remain. Most critically, Git's global configuration home is the untrusted checkout itself, allowing a committed `.gitconfig` to configure executable Git behavior on the host. No passing `security_review` receipt should be recorded for this HEAD.

## Exact-HEAD evidence

- Focused Trust CI security suites (`test_policy`, `test_workspace`, `test_runner`, holdout, signing, PostgreSQL) — **92 passed, 10 skipped**; skips are the disclosed conditional PostgreSQL tests with no `TRUST_CI_TEST_DATABASE_URL`.
- Full root discovery — **223 passed**.
- Full Trust CI discovery — **192 passed, 10 skipped**.
- Initial `git status --short` was clean and `git rev-parse HEAD` returned `25b9562144c774e125851019c02de6eca7a4a828`.

## Review-4 closure

| Prior finding | Result | File/line evidence |
| --- | --- | --- |
| SEC-R4-001 asymmetric policy/path normalization | **Closed** | `ApprovalRule.from_dict()` and `Policy.required_scopes()` both use exact `_validated_repo_relative()` values without rewriting (`trust-ci/src/adaptive_trust_ci/policy.py:63-73,279-312`). Tests cover `.grok-stack/**`, `.grok/**`, `.github/**`, `.coveragerc`, literal backslash, Unicode, LF, and tab, including action-required and valid signed-approval runner flows. |
| SEC-R4-002 post-allocation Git output limits | **Closed for direct output/record allocation** | `_run_bounded_process()` reads at most the remaining allowance plus one byte (`trust-ci/src/adaptive_trust_ci/workspace.py:87-159`). `_NulPathCollector.feed()` enforces aggregate bytes, current record bytes, and record count before retaining each record (`workspace.py:31-67`). Real-Git and synthetic exact/over-bound tests pass. |
| Exact SHA/path fail-closed behavior | **Pass** | Checkout retains PR-ref/HEAD equality checks and `_changed_files()` verifies both commit objects before explicit `git diff ... <base> <head> --` (`workspace.py:184-220,239-268`). Invalid UTF-8, unsafe paths, malformed NUL records, output overflow, and direct-process timeout tests pass. |
| Earlier parser/symlink/provenance/signing boundaries | **Remain closed for reviewed vectors** | Focused holdout, runner, signing, surrogate, malformed provenance, ancestor-symlink, golden replay, and mutation tests pass unchanged. |

## Findings

### SEC-R5-001 — P0 / blocking: a committed `.gitconfig` can enable repository-controlled host execution

`GitWorkspace._git_env()` sets `HOME` to `self.path`, the checked-out repository root, while only disabling system configuration (`trust-ci/src/adaptive_trust_ci/workspace.py:343-359`). After exact-head checkout, a repository-controlled root file named `.gitconfig` is therefore Git's normal global configuration file for every subsequent trusted-host Git invocation.

This violates the class invariant at `workspace.py:162-163` that repository code is never executed. Git configuration can name executable behavior such as `core.fsmonitor`; `assert_unchanged()` invokes host `git status` after checkout (`workspace.py:218-229`), and `reset()` invokes additional host Git commands (`workspace.py:283-288`). Output streaming, timeouts, and fail-closed parsing happen only after Git has loaded that untrusted configuration and potentially launched the configured process. The committed policy protects `.gitconfig` only if a matching rule exists, but approval cannot make PR code safe to execute inside the privileged checkout component.

Required repair:

- isolate Git's global config from the worktree, for example with a trusted private HOME outside the checkout and/or an explicit trusted `GIT_CONFIG_GLOBAL` target; keep system config disabled;
- preserve the trusted in-repository `.git/config` created by `GitWorkspace`, but do not read any worktree-owned config or executable hook/filter/fsmonitor setting;
- add an isolated regression proving a committed root `.gitconfig` containing executable Git configuration is ignored by diff, reset, and status, without running repository code.

### SEC-R5-002 — P1 / blocking: timeout cleanup can leave process-group descendants alive

`_run_bounded_process()` correctly creates a new session and calls `_terminate_process()` on timeout, overflow, or consumer errors (`workspace.py:97-159`). `_terminate_process()` sends SIGTERM to the group, but returns immediately when `process.wait(timeout=1)` observes that the direct leader exited (`workspace.py:70-84`). It does not verify that the process group is gone or send SIGKILL after the grace interval when a descendant ignored SIGTERM.

The current tests prove cleanup only for a single direct Python child (`trust-ci/tests/test_workspace.py:108-184`); they do not cover a leader that exits on SIGTERM while a same-session descendant remains. For fetch helpers or configuration-launched processes, this can leave a host process running after the bounded call has reported failure, potentially retaining inherited environment and pipe descriptors.

Required repair: after the grace period, target the process group with SIGKILL regardless of whether the leader has already exited (treat a missing group as success), then reap the direct child and close pipes. Add a synthetic leader/descendant regression where the descendant ignores SIGTERM and prove the entire process group is gone after timeout and output overflow.

## Security conclusion

The exact approval-scope and bounded-streaming remediation is technically effective and all earlier M1 parser/provenance findings remain closed. Nevertheless, the trusted checkout still consumes worktree-controlled global Git configuration before its safety checks, creating a direct host-code-execution boundary violation; process-group cleanup is also incomplete for descendants. Both require remediation and a new exact-HEAD security review. Local evidence remains advisory and cannot replace the App-owned policy-epoch exact-SHA check or external signed approvals.
