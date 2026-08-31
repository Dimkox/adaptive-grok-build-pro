# Code review 7 — atomic workspace allocation remediation

## Verdict: PASS

Reviewed exact commit `98649e4e1e6a971fb802bc934eb5680de529e18a` (Git tree `a78118c8e420d152add5779046ee257ba02e8203`, verification fingerprint `903ba95998867a24016ce04c6055114855e63601593699ca8355179a0e8f55ba`) against `9a6e27c193ec944a149e452ff7591fbc7493238c`, the review-6 constructor-leak finding, and the relevant workspace lifecycle tests. The prior blocker is closed. No correctness, compatibility, maintainability, or lifecycle regression was found in the bounded remediation.

## Finding disposition

No open findings.

- `trust-ci/src/adaptive_trust_ci/workspace.py:235-252` keeps both allocation references local and nullable until checkout creation/chmod, config-home creation/chmod, and XDG-directory creation have all succeeded. Any exception rolls back every successfully allocated tree in reverse order before a bare `raise`, and the object publishes `self.path` and `self.config_home` only after complete initialization. This closes the checkout-chmod, second-`mkdtemp`, config-chmod, and XDG-mkdir leak paths identified in review 6.
- `workspace.py:35-41` makes rollback cleanup best-effort and non-masking: a cleanup exception cannot replace the original constructor exception, and failure while removing one path does not prevent attempting the other path. A direct probe in which `shutil.rmtree` itself raised confirmed that the original allocation exception object was re-raised.
- `workspace.py:360-362` preserves normal cleanup behavior. Both directory removals use `ignore_errors=True`; calling `cleanup()` twice remains harmless and leaves no workspace entries.
- `trust-ci/tests/test_workspace.py:17-95` adds failure-injection coverage for every allocation boundary and verifies exception identity plus zero leftover directories. It also exercises normal cleanup idempotency. The tests match the production allocation sequence and would reproduce the review-6 XDG leak against the previous implementation.

## Verification evidence

- `git diff --check 9a6e27c..98649e4`: PASS.
- Focused `GitWorkspaceLifecycleTests`: 5/5 passed.
- Direct XDG-construction failure probe: PASS; the original exception was preserved and `constructor_failure_leftovers=[]`.
- Direct rollback-cleanup failure probe: PASS; a synthetic `shutil.rmtree` failure did not mask the original constructor exception.
- Clean archived exact-HEAD Trust CI suite: 200 total, 190 passed, 10 PostgreSQL integration tests skipped because `TRUST_CI_TEST_DATABASE_URL` was not configured.
- `python3 scripts/grok_verify.py --mode pr --no-record --json`: PASS; 223 root tests passed, typed-spec coverage was 6/6, and diff/schema/ruff/bandit checks passed.

This report is local exact-tree evidence only. It does not substitute for the App-owned policy-epoch Trust CI check or any required external signed approval.
