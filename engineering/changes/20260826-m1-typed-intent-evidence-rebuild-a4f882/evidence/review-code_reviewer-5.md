# Code review 5 — M1 bounded policy/path remediation

## Verdict: BLOCKED

Reviewed exact commit `25b9562144c774e125851019c02de6eca7a4a828` (tree `bc48515d077708ef9bde3138cffb0bad1eac4ccd`, verification fingerprint `727c6bcb602151db5112ba2f62cb2e130ea66b1193b84d2fe7d98f86d1e4aeaa`) against `ee9ed6ada12f78f808a12df311a41d7888ca9d30`, with product remediation commit `3088225` and the following self-learning-only commit inspected separately. The prior dot-glob normalization and post-allocation output-limit blockers are closed. One process-group cleanup defect remains in the new bounded runner, so the exact candidate is not ready for a passing code-review receipt.

## Blocking finding

### P1 — Overflow/timeout cleanup can return while a descendant in the bounded process group is still running

`trust-ci/src/adaptive_trust_ci/workspace.py:70-84` sends `SIGTERM` to the new process group, then waits only for the `Popen` leader. If that leader exits promptly, line 77 returns immediately and never checks whether the process group still contains descendants or sends the intended `SIGKILL` escalation to them. `start_new_session=True` at lines 97-106 correctly creates the group, but the cleanup decision is bound to leader lifetime rather than group lifetime.

This is reproducible without races:

1. The bounded leader starts a same-group descendant which closes inherited streams, ignores `SIGTERM`, records its PID, and sleeps.
2. The leader continuously writes stdout until the 128-byte limit raises the expected `WorkspaceError`.
3. Cleanup sends group `SIGTERM`; the leader exits, `process.wait()` returns, and `_terminate_process()` returns.
4. Immediately after `_run_bounded_process()` returned, `os.kill(descendant_pid, 0)` succeeded: `grandchild_survived_cleanup=True`. The review probe then explicitly killed the temporary descendant.

The existing overflow and timeout tests at `trust-ci/tests/test_workspace.py:102-121,162-182` record and assert only the leader PID, so both pass while this leak remains. The helper is used for Git commands, including fetch operations that can themselves have helper processes. A surviving helper can outlive the failed bounded operation and accumulate across retries, undermining the remediation's resource-bound/process-cleanup guarantee.

Required remediation: keep the process-group ID, reap the leader as required, but base escalation on whether the group still exists after the TERM grace period rather than returning merely because the leader exited. Ensure any surviving group members receive `SIGKILL`, close/reap all resources available to the parent, and add an adversarial regression with a promptly exiting leader plus a same-group descendant that ignores `SIGTERM`; assert the descendant is gone after overflow and timeout paths return.

## Prior blockers verified closed

- **Exact approval globs:** `trust-ci/src/adaptive_trust_ci/policy.py:63-73,279-312` validates but does not rewrite authored patterns or changed paths. `.grok-stack/**`, `.grok/**`, `.github/**`, `.coveragerc`, literal backslashes, Unicode, LF, and tab retain exact identity and bind governance scope. Unsafe/non-string/absolute/traversal/control/surrogate/oversized inputs fail closed.
- **End-to-end scope behavior:** `trust-ci/tests/test_runner.py:294-369,537-587` exercises real Git identity plus missing-scope `action_required`/zero commands and exact signed approval before execution for dot-prefixed and unusual targets. Focused policy and runner tests passed.
- **Preallocation/output limits:** `workspace.py:33-67,87-159` replaces `capture_output` with selector-driven streaming. Each read is capped at the remaining allowance plus one byte; stdout/stderr overflow terminates the operation; NUL records enforce aggregate bytes, count, and per-record bytes incrementally before returning the bounded tuple. Exact/over-bound, chunk-spanning, count, record-size, stderr, stdout, timeout, diff, and status tests passed.
- **Docs-only follow-up:** `25b9562` changes only `mistakes.md` and accurately records that an earlier abbreviated commit ID was expanded by hand; it introduces no product regression.

## Verification evidence

- `git diff --check ee9ed6a..25b9562`: PASS.
- Focused policy/workspace/runner suite: 13 passed.
- Clean archived exact-HEAD Trust CI suite: 192 passed, 10 PostgreSQL integration tests skipped because `TRUST_CI_TEST_DATABASE_URL` was not configured.
- `python3 scripts/grok_verify.py --mode pr --no-record --json`: PASS; 223 root tests passed, current typed spec coverage is 6/6, and diff/schema/ruff/bandit checks passed.
- Independent descendant-cleanup probe: FAIL as described above; same-group SIGTERM-ignoring descendant remained alive after bounded stdout-overflow cleanup returned.

This report is local exact-tree evidence only. It does not substitute for the App-owned policy-epoch Trust CI check or any required external signed approval.
