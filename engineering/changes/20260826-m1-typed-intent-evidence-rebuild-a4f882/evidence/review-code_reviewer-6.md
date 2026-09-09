# Code review 6 — M1 process/config isolation remediation

## Verdict: BLOCKED

Reviewed exact commit `9a6e27c193ec944a149e452ff7591fbc7493238c` (tree `dd7e3d961886ffdbcbb7f6aa1934b50f32eedc4b`, verification fingerprint `c40ea6c2dad06e167963e1c32a6374868e914b3375a4fc74d61cce1f232b9d60`) against `25b9562144c774e125851019c02de6eca7a4a828`, the review-5 finding, and relevant surrounding Trust CI lifecycle code. The descendant cleanup blocker is closed and normal Git configuration isolation is correct. One constructor-failure cleanup defect remains, so the exact candidate is not ready for a passing code-review receipt.

## Blocking finding

### P1 — Partial private-config initialization leaks one trusted directory per failed/retried workspace construction

`trust-ci/src/adaptive_trust_ci/workspace.py:226-236` creates the checkout, then creates `self.config_home`, changes its mode, and creates `config_home/xdg`. The exception handler removes only `self.path`; it never removes `self.config_home` if `mkdtemp()` succeeded and either `chmod()` or `xdg.mkdir()` failed. Because construction raises, the normal `cleanup()` at lines 344-346 cannot be invoked on the unreturned object. The checkout `chmod()` at line 227 is also outside the cleanup guard, so a failure there leaves the just-created checkout directory.

Direct fault injection reproduced the new config leak: forcing only `(config_home / "xdg").mkdir()` to raise `OSError` left `constructor_failure_leftovers=['trust-ci-config-config-l-dpmlmwpv']` under the workspace base while the checkout directory was removed. In the worker flow, construction happens before the `try/finally` that owns a successfully returned workspace, so transient filesystem/inode/permission failures can leak another directory on every retry and amplify the condition preventing progress.

Required remediation: make allocation atomic from the first `mkdtemp()`. Initialize both path references safely, wrap checkout chmod plus config-home creation/chmod/XDG creation in one exception guard, and remove every successfully allocated directory on any constructor exception. Add failure-injection regressions for checkout chmod, config-home chmod, and XDG mkdir, asserting that the base directory has no leftover `trust-ci-*` or `trust-ci-config-*` entries. Preserve the current idempotent normal cleanup behavior.

## Prior finding verified closed

- `workspace.py:72-128` tracks the original PGID independently of leader lifetime, refuses the worker's own group, tolerates ESRCH, polls/reaps the leader, checks group existence through a TERM grace period, escalates survivors to SIGKILL, and fails closed if the group remains.
- The exact review-5 adversarial probe now reports `grandchild_survived_cleanup=False` rather than leaving the SIGTERM-ignoring same-group descendant alive.
- `trust-ci/tests/test_workspace.py:274-307` covers promptly exiting leaders plus SIGTERM-ignoring descendants for stdout overflow, stderr overflow, and timeout; all cases passed. The tests include emergency oracle cleanup and own-group/nonexistent-group cases.
- No unresolved practical PGID/lifetime/reaping regression was found. A process that deliberately creates a different session/process group is outside this same-group cleanup primitive; Git commands are additionally isolated from repository-controlled hooks/fsmonitor/config execution.

## Git configuration isolation verified

- `workspace.py:398-420` points `HOME` and `XDG_CONFIG_HOME` outside the checkout, disables global/system Git configuration and system attributes, and applies command-scope `core.hooksPath=/dev/null` plus `core.fsmonitor=false`; the authenticated HTTP header is present only for authenticated operations.
- The real-repository regression at `trust-ci/tests/test_workspace.py:122-169` commits executable fsmonitor, hook, and external-diff settings in a root `.gitconfig`, exercises diff/reset/status, and proves no marker executes, exact LF path identity remains intact, authenticated config is appended without dropping isolation, and normal cleanup removes the trusted config home.
- Existing exact path, scope, NUL streaming, byte/count/record limits, invalid UTF-8, and signed provenance behavior remains unchanged in the remediation diff and passing suites.

## Verification evidence

- `git diff --check 25b9562..9a6e27c`: PASS.
- Focused `test_workspace` suite: 10 passed.
- Exact review-5 descendant survivor probe: PASS after remediation (`grandchild_survived_cleanup=False`).
- Constructor failure-injection probe: FAIL as described above; private config directory remained after XDG creation failure.
- Clean archived exact-HEAD Trust CI suite: 195 total, 185 passed, 10 PostgreSQL integration tests skipped because `TRUST_CI_TEST_DATABASE_URL` was not configured.
- `python3 scripts/grok_verify.py --mode pr --no-record --json`: PASS; 223 root tests passed, current typed spec coverage is 6/6, and diff/schema/ruff/bandit checks passed.

This report is local exact-tree evidence only. It does not substitute for the App-owned policy-epoch Trust CI check or any required external signed approval.
