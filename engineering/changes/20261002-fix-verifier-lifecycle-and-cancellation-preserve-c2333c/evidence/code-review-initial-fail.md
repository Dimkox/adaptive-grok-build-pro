# Independent code review — local FAIL

Route-selected role: code_reviewer; route c2333ca04e25. Review scope is reconstructed issue 226, five product files and the complete active change package. No additional agents were dispatched.

Source candidate: `<local-path>`. Base: `63799f8760d3a55028d83ab5ff0116ececf8f7d1`. HEAD before/after: `30297838c1a08a0ebe3944af07dfb69968202587`. Fingerprint before/after: `dd55524155ae434f96e778543ca8b789caa66ac3ab6d64b121bdff379f642e16`; status clean before/after.

Scratch: `<local-path>`, cloned using `git clone --no-hardlinks --no-checkout <candidate> <scratch>` and detached checkout of exact HEAD. Parent and review directory are owner UID 1000, mode 0700, non-sticky. Unmutated scratch fingerprint matches source; all mutations were reverted with explicit patches, scratch product status clean afterward. Report/probe files reside only outside its product checkout in the reviewer directory.

reviewed-tree-modified: no

## Blocking finding

**Medium: output scratch cleanup still discards completed results and cancellation.** `.grok-stack/adaptive_grok/python_test_runner.py:202` opens both output files as ordinary context managers. The `return result` at line 252 and `cancelled.check(result)` at line 251 execute before their exits. An OSError closing either output file replaces the completed ProcessResult or RunCancelled. The caller receives no result/output, and `_command_check` (verification.py:439-447) catches only RunCancelled; the outer verifier catches cancellation exceptions, not this OSError. This violates AC-001 scratch-cleanup preservation and AC-002 cancellation metadata preservation.

Executable fault probe on unmutated product: `taskset -c 4 python3 <local-path>`. The probe wraps the real TemporaryFile, really closes it, and raises OSError from the wrapper's finally; the real child prints a specific failure and exits 7. Second case introduces SIGTERM during the real owned-group cleanup before the same failing output close. Observed:

```text
LOST_RESULT OSError injected output scratch close failure has_result=False
LOST_CANCELLATION OSError injected output scratch close failure has_result=False
```

Retain the computed result and primary cancellation exception across output-handle cleanup, recording cleanup_error or adding a cleanup note without replacing the primary result/exception. Add completed pass/fail and cancellation regressions for this particular boundary. No candidate repair was performed by this reviewer.

## Executed checks and mutation controls

Baseline: `taskset -c 4 python3 -m unittest tests.test_verifier_recovery -q` — 20 tests in 7.975s, OK. This executes receipt/report verdict retention, cancellation stages, TERM-resistant owned child cleanup with unrelated child survival, coverage malformed input, temporary-directory cleanup failure, UTF-8 output, receipt publication faults and HEAD fencing. It does not cover the output-file close boundary above.

Three independent mutants were installed simultaneously in separate functions with explicit apply_patch edits; each targeted test exercises its corresponding boundary:

| Mutant | Targeted control | Result |
|---|---|---|
| M1: clear report checks in receipt-recording exception handler | VerifierRecoveryTests.test_receipt_failure_keeps_completed_verdict_and_report | killed: eight subcases raise StopIteration because original check disappeared |
| M2: disable explicit receipt git_head mismatch check | DurableReceiptRecoveryTests.test_same_tree_new_head_invalidates_receipt | killed: expected head gap absent |
| M3: make owned-group _stop return immediately | OwnedRunnerRecoveryTests.test_running_term_resistant_child_is_reaped_and_unrelated_child_survives | killed: owned PID remained alive, ProcessLookupError assertion failed; harness finally terminated owned and unrelated fixtures |

Exact combined command:

```bash
taskset -c 4 python3 -m unittest tests.test_verifier_recovery.VerifierRecoveryTests.test_receipt_failure_keeps_completed_verdict_and_report tests.test_verifier_recovery.DurableReceiptRecoveryTests.test_same_tree_new_head_invalidates_receipt tests.test_verifier_recovery.OwnedRunnerRecoveryTests.test_running_term_resistant_child_is_reaped_and_unrelated_child_survives -v
```

Observed: three tests in 2.666s, FAILED (failures=2, errors=8). After reverting all three mutations, the same three controls with `-q` passed in 2.870s. No surviving/inconclusive mutant is concealed. These three outcomes do not establish a blanket mutation score.

## Inspected coordinator evidence and static scope

Read the actual candidate diff and surrounding runner, verifier, CLI and receipt code, typed acceptance criteria, package requirements/design/test plan/rollback/release, route and evidence accounting. The diff leaves the verification scope selector and grant behavior untouched; that is static inspection, not a separately executed guarantee. Initial concern about HEAD changing during verification was resolved: util.tree_fingerprint includes exact Git HEAD, so source-stability also fences a same-tree HEAD transition.

Inspected coordinator `.grok-stack/runtime/final-verify.json`, created 2026-10-02T23:26:19+00:00, matching reviewed fingerprint. It reports pass, completed, mode pr, full-pr-suite, no scope skips, actual route/PR bases matching supplied base; Core, coverage, factory-unit and factory-postgres-exit pass. Workflow-artifacts explicitly skips because unconfigured. This is coordinator evidence inspected, not a claim that this reviewer executed the full suite. The 172 unchanged tests were not rerun.

## Capacity and limitations

Startup discovery was performed and recorded in reviewer `capacity.md` before repository inspection. Host 14 physical cores / 28 online logical CPUs; initial process affinity 22 CPUs; cgroup v2 ancestor effective cpuset 0-27 with no finite quota found. Child-only widening probe verified 28 allowed CPUs and unchanged cgroup bounds. All reviewer test/probe commands used assigned one-worker CPU 4; no controller affinity was changed.

Unexecuted claims: real power-loss persistence and actual disk-full/permission failures (deterministic boundary faults only); every possible subprocess descendant escape/session behavior; repeated-signal storm; full suite execution by this reviewer; compatibility of all legacy receipt consumers. Static conclusions above remain static. Declined to judge: external exact-SHA Trust CI, human approvals, merge eligibility, deployed trust policy/holdout, live deployments and release authority. No external writes, secret reads or approval operations occurred.

Disposition: **local FAIL / not ready** until the output-file cleanup finding is fixed and freshly verified/reviewed. This report is independent workflow evidence, never merge authority.
