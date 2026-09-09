# Test re-review 6 — M1 process-group and trusted Git-config remediation

## Verdict

**BLOCKED**

Reviewed exact repository HEAD `9a6e27c193ec944a149e452ff7591fbc7493238c` against prior reviewed HEAD `25b9562144c774e125851019c02de6eca7a4a828`, original review base `0a4dd0a867c876f99a8fe3580c9f0d47c90e3105`, remediation-5, and the active M1 package. The worktree was clean at review start. Concurrent route reviewers later wrote only untracked review reports; no product file changed during this review.

The review-5 process-group blocker is closed, and the committed checkout `.gitconfig` isolation regression is materially sensitive and passes. A distinct P1 temporary-resource lifecycle defect remains in constructor failure paths and has no regression, so this HEAD must not receive a passing `test_review` receipt.

## Blocking finding

### TEST-R6-001 — P1: partial `GitWorkspace` construction leaks trusted temporary directories

`GitWorkspace.__init__()` allocates the checkout with `mkdtemp()` and then runs its first `chmod()` before entering the exception guard. If that `chmod()` fails, the newly allocated checkout remains. Inside the guard, it allocates `self.config_home`, changes its mode, and creates `config_home/xdg`, but the handler removes only `self.path`. If config-home `chmod()` or XDG creation fails, construction raises without returning an object and the trusted config directory remains; `JobRunner` cannot call `cleanup()` on an object it never received.

Independent fault injection made only the second `chmod()` fail and reproduced the leak:

```text
constructor_error synthetic config-home chmod failure
leftovers_after_failed_constructor ['trust-ci-config-lifecycl-6evy0ytf']
```

The probe ran under an enclosing temporary directory, so the leaked test directory was removed after evidence capture. This is a production lifecycle failure: repeated workspace retries can leave another directory on each transient permission/filesystem/inode error and amplify resource exhaustion. The committed lifecycle test exercises only successful construction plus normal, idempotent cleanup and cannot detect any partial-construction leak.

Required repair: initialize both path references safely and guard every operation starting with the first checkout `mkdtemp()`/`chmod()`. On any constructor exception, remove every directory that was successfully allocated. Add fault-injection regressions for checkout chmod, config-home chmod, and XDG mkdir; each must assert the workspace base contains no `trust-ci-*` or `trust-ci-config-*` entry afterward. Preserve the existing normal double-cleanup behavior.

## Review-5 blocker closure

The process-group remediation is correctly covered and independently reproduced:

- The original PGID is retained independently of leader lifetime. Cleanup sends TERM, polls group existence while reaping the leader, escalates surviving members to KILL, verifies group disappearance, and refuses the worker's own process group.
- The committed real-process regression covers stdout overflow, stderr overflow, and timeout with a promptly exiting leader and a same-group descendant that ignores SIGTERM. It asserts the descendant PID is absent after return and has emergency cleanup in `finally`, preventing a failed oracle from leaking its own probe.
- The full workspace suite plus three additional repetitions of the resistant-descendant regression passed: 14 test executions, no survivors.
- Independent stdout-overflow and timeout probes checked all three postconditions directly: leader absent, descendant absent, and `_process_group_exists(original_pgid) == False`. Probe cleanup also confirmed no descendant remained.

## Committed `.gitconfig` and normal config lifecycle

- The trusted config home is mode-isolated beside rather than inside the checkout. `HOME` and `XDG_CONFIG_HOME` point there; global/system Git config and system attributes are disabled; command-scope config neutralizes hooks and fsmonitor.
- The authenticated HTTP header is appended only for authenticated operations without dropping the isolation keys.
- The real repository regression commits `.gitconfig` containing executable fsmonitor, hooks, and external-diff settings, then exercises exact diff, reset, and status. No marker executes, LF-containing path identity remains exact, and the normal cleanup removes the config home. The test's tear-down calls cleanup again, also exercising idempotence.
- This successful-path coverage does not compensate for TEST-R6-001's missing partial-construction cases.

## Independent exact-HEAD evidence

- Initial identity: `git rev-parse HEAD` -> `9a6e27c193ec944a149e452ff7591fbc7493238c`; initial `git status --short` was empty.
- Focused/repeated workspace remediation tests: PASS, 14 executions.
- Independent process-group probes: PASS for stdout overflow and timeout; leader, resistant descendant, and original group all absent after return.
- Partial-constructor config-home probe: FAIL as described in TEST-R6-001.
- Default Trust CI discovery, first run: PASS, 195 total, 185 executed successfully, 10 conditional PostgreSQL skips.
- Default Trust CI discovery, immediate second run: PASS, 195 total, 185 executed successfully, 10 conditional PostgreSQL skips.
- Holdout identity before and after both runs: digest `e2de03333ac37e6478433ad37486f6ee904ae8ba8054c86481c04eb7d56fcd64`; complete regular-file set exactly `change_spec_validate.py`, `validate.py`.
- Full root discovery: PASS, 223/223.
- `python3 -m compileall -q .grok-stack/adaptive_grok scripts trust-ci/src`: PASS.
- `git diff --check 0a4dd0a..HEAD`: PASS.
- `python3 scripts/grok_verify.py --mode pr --no-record --json`: PASS at Git HEAD `9a6e27c193ec944a149e452ff7591fbc7493238c`; active spec valid with 6/6 criteria mapped; fingerprint `54458f41f97100bfea2f6275bdb9de9e04fa223336418270f278d99c9a31b24d`. Concurrent untracked code/security review reports were present by this preflight, so the fingerprint is not represented as a clean-HEAD-only tree fingerprint.

The 10 PostgreSQL integration tests were honestly skipped because `TRUST_CI_TEST_DATABASE_URL` is not configured and are not claimed as executed database evidence. All local evidence remains advisory and does not replace the App-owned policy-epoch check or required external approvals.

## Conclusion

Resistant-descendant termination, actual group removal, committed-config isolation, normal cleanup, full suites, and holdout hermeticity pass. The unguarded partial-construction lifecycle remains a reproducible resource leak and requires repair plus failure-injection coverage before another exact-HEAD test review.
