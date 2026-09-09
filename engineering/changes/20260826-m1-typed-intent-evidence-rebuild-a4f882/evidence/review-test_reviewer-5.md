# Test re-review 5 — M1 policy paths and bounded workspace streaming

## Verdict

**BLOCKED**

Reviewed exact repository HEAD `25b9562144c774e125851019c02de6eca7a4a828` against remediation predecessor `ee9ed6ada12f78f808a12df311a41d7888ca9d30`, original review base `0a4dd0a867c876f99a8fe3580c9f0d47c90e3105`, the approved M1 design/plan, active package, remediation-4 claims, and preserved earlier test reviews. The worktree was clean at review start. Concurrent route reviewers later added untracked review reports; no product file changed during this review.

The approval-glob identity bypass and pre-capture memory-bound blocker from wave 4 are materially repaired. Policy/path regressions, bounded incremental parsing, full suites, and holdout hermeticity pass. One P1 process-cleanup defect remains and is hidden by an incomplete test oracle, so no passing `test_review` receipt should be recorded for this HEAD.

## Blocking finding

### TEST-R5-001 — P1: overflow/timeout cleanup can leave a descendant in the bounded command's process group alive

`_run_bounded_process()` correctly starts the command in a new session and calls `_terminate_process()` on stdout overflow, stderr overflow, timeout, or consumer failure. `_terminate_process()` sends SIGTERM to the process group, but returns immediately when the group leader exits (`trust-ci/src/adaptive_trust_ci/workspace.py:70-84`). It sends the intended SIGKILL escalation only when `process.wait(timeout=1)` times out for the leader. A descendant that ignores SIGTERM therefore survives whenever the leader exits promptly.

The committed tests at `trust-ci/tests/test_workspace.py:102-121` and `162-182` create only one process and assert only that leader PID is gone. They cannot detect a surviving subprocess/helper even though the implementation deliberately uses `start_new_session=True` and group-directed signals. The stderr-overflow test does not assert cleanup at all.

Independent adversarial probes spawned a leader plus a same-group descendant that ignored SIGTERM. Both failure paths returned the expected controlled `WorkspaceError`, but the descendant was still present immediately after `_run_bounded_process()` returned:

```text
stdout overflow -> stdout byte limit exceeded
sigterm_ignoring_descendant_alive_after_return True

timeout -> process exceeded its timeout
sigterm_ignoring_descendant_alive_after_timeout True
```

Both probe descendants were explicitly killed and confirmed absent before the review continued. This is not merely missing coverage: a persistent Trust CI worker can leak Git helpers or other descendants after a bounded operation is declared terminated, undermining the resource-containment objective of this remediation.

Required repair: after the SIGTERM grace period, ensure the complete original process group is gone and issue SIGKILL to remaining group members even when the leader has already exited; still reap the leader deterministically. Add regressions with a SIGTERM-resistant descendant for overflow and timeout, asserting the whole group is absent after return. Cover stderr overflow or a shared termination helper path so every exception route uses the same guarantee.

## Closed wave-4 boundaries

- Approval globs preserve `.grok-stack/**`, `.grok/**`, `.github/**`, `.coveragerc`, literal backslashes, Unicode, LF, and tab. Full runner regressions prove missing governance approval produces `action_required` with no commands, and an exact signed scope permits execution.
- Unsafe absolute/traversal/empty-component/NUL/control/surrogate/non-string and invalid-UTF-8 policy inputs fail closed without rewriting legitimate repository identities.
- Git stdout/stderr is read incrementally with at most the remaining allowance plus one byte; overflow raises before unbounded capture and terminates the leader.
- NUL path collection enforces aggregate bytes, path count, and per-path bytes while streaming across chunk boundaries. Real Git diff/status tests preserve unusual identities and exercise aggregate, count, and record-limit rejection.
- Independent missing-boundary probes confirmed policy authored/runtime paths accept exactly 4096 UTF-8 bytes and reject 4097, collectors accept/reject exact/over count and per-path thresholds, and status prefix bytes are excluded correctly from the path-length allowance. These exact policy/count/path boundary probes are not committed regressions; adding them with the required cleanup regression would make the documented limit matrix durable.

## Full-suite and holdout evidence

- Focused `test_policy`, `test_workspace`, and three end-to-end runner path/approval tests: PASS, 31/31.
- Default Trust CI discovery, first run: PASS, 192 tests total, 10 conditional PostgreSQL skips, no failures.
- Default Trust CI discovery, immediate second run: PASS, 192 tests total, 10 conditional PostgreSQL skips, no failures.
- Before and after each Trust run, the holdout digest was exactly `e2de03333ac37e6478433ad37486f6ee904ae8ba8054c86481c04eb7d56fcd64`; the complete regular-file set remained exactly `change_spec_validate.py` and `validate.py` with no bundle `__pycache__`.
- Full root discovery: PASS, 223/223.
- `python3 -m compileall -q .grok-stack/adaptive_grok scripts trust-ci/src`: PASS.
- `git diff --check 0a4dd0a..HEAD`: PASS.
- `python3 scripts/grok_verify.py --mode pr --no-record --json`: PASS at Git HEAD `25b9562144c774e125851019c02de6eca7a4a828`; active spec valid with 6/6 mapped criteria; fingerprint `50869ab504d3bba1c98d31ffb7fef5d428d208d97d7e1da34b2a9e85562d9303`. The fingerprint includes the concurrently written untracked code-review report disclosed above, so it is not represented as a clean-HEAD-only tree fingerprint.

The 10 PostgreSQL integration tests were honestly skipped because `TRUST_CI_TEST_DATABASE_URL` is not configured and are not claimed as executed database evidence. Also, remediation-4's phrase “192 tests passed, with 10 ... skips” overstates the result: unittest reports 192 total tests, of which 10 were skipped, leaving 182 executed successfully.

## Conclusion

The default suites and digest hermeticity are green, and the original policy/path/memory-allocation blockers are closed. Nevertheless, the bounded-process cleanup contract is not satisfied for the full process group and the current oracle cannot see that failure. Return the repair to the selected write owner and perform a new exact-HEAD review after adding the descendant-cleanup regressions.
