# Independent test review — FAIL

Reviewer: route-selected test_reviewer, independent of implementation. Route c2333ca04e25; change 20261002-fix-verifier-lifecycle-and-cancellation-preserve-c2333c. This is bounded local preflight evidence, not merge authority.

## Identity and isolation

Candidate: <local-path> Exact HEAD before and after: 30297838c1a08a0ebe3944af07dfb69968202587. Comparison base: 63799f8760d3a55028d83ab5ff0116ececf8f7d1. Candidate tree fingerprint before and after: dd55524155ae434f96e778543ca8b789caa66ac3ab6d64b121bdff379f642e16. Candidate tracked/staged/unstaged/untracked inventory was clean before and after.

Private scratch: <local-path> Parent .review-scratch and unique scratch are directories mode 0700, non-sticky. Snapshot was created with git clone --no-hardlinks --no-checkout followed by detached checkout of the exact HEAD. Snapshot HEAD and fingerprint equaled candidate before testing, and again after reverting all three scratch-only mutants; final snapshot Git status was clean. No candidate commands imported modules, ran tests, wrote bytecode/cache, or changed refs/index. Candidate identity checks used modules imported from the private snapshot. Tests used private TMPDIR below scratch. No subagents, external writes, credentials, deployed material, selector changes, or issue-227/grant work.

reviewed-tree-modified: no

Startup capacity recorded before repository inspection in capacity.json. lscpu: 14 physical cores, 28 online logical CPUs (0-27); nproc --all: 28; initial nproc: 22 and affinity 0,1,8-27. Actual v2 membership /user.slice/user-1000.slice/session-2050.scope was resolved using /proc/self/cgroup and /proc/self/mountinfo. Visible applicable cpu.max values were max 100000; inherited effective cpuset 0-27. Root cpu.max was absent, so quota uncertainty was handled conservatively. Bounded child-only taskset -c 5 probe succeeded: child nproc=1, affinity=5, same cgroup. All test commands allocated one worker on CPU 5; no controller affinity change. capacity.json and identity-before.json/identity-after.json retain raw evidence.

## Scope and inspected requirements

Inspected actual base..HEAD diff and surrounding python_test_runner.py, verification.py, receipts.py, scripts/grok_verify.py, tests/test_verifier_recovery.py, relevant existing runner controls and fixture isolation. Read route and requirements/test-plan. AC-001..003 require primary result/report retention, failing gates for failed evidence, signal windows and first-signal retention, bounded owned-process cleanup, atomic durable receipt publication and exact HEAD/tree/check/scope/terminal bindings. AC-004 excludes selector/grant/release/deployed changes.

The coordinator supplied completed full-PR-suite evidence on this exact HEAD. I did not rerun that suite or treat that supplied result as independently executed evidence. This review executes focused recovery and relevant descendant controls plus independent fault/mutation probes.

## Executed controls and exact commands

All commands below ran in private snapshot. Common command prefix E is:

`taskset -c 5 env TMPDIR=<local-path> PYTHONDONTWRITEBYTECODE=1 GROK_TEST_WORKERS=0`

1. `E python3 -m unittest tests.test_verifier_recovery -v`: 20 tests in 11.597s, OK, exit 0. Controls exercise original pass/fail retention; receipt OSError/RuntimeError/ValueError/TypeError; cancellation before dispatch/spawn, TERM-resistant child, coverage, post-result, receipt replacement and report output; npm prior failure; stdout failure with structured stderr fallback; scratch/owned cleanup errors; malformed/truncated coverage; invalid UTF-8; write/replace/file-fsync/directory-fsync faults; exact HEAD staleness and receipt report bindings. Real cancellation control confirms direct owned child reaped and unrelated private group survives.

2. `E python3 -m unittest tests.test_python_test_runner.PythonTestRunnerTests.test_timeout_stops_owned_descendant_process tests.test_python_test_runner.PythonTestRunnerTests.test_controller_exit_stops_owned_descendant_process -v`: 2 tests in 1.141s, OK, exit 0. These relevant existing controls check timeout=124 and descendant termination after leader exit.

3. `E python3 <local-path>`: exit 0. Reviewer-created probes printed five PASS results: SIGINT then SIGTERM retains first signal and exit 130 without spawning; quick-exit 4MiB output is bounded to 2097152 captured stdout bytes and fails with 124; exited leader's TERM-resistant descendant stops within <5s; original assertion plus primary receipt-binding error plus secondary unlink error remain in structured failed report; post-result fingerprint OSError retains the original completed failure in structured failed report. Probe source is retained in scratch. An initial immediate descendant-state assertion observed a transient live state directly after SIGKILL; bounded polling for up to one second, consistent with existing Linux controls, confirmed termination. This does not claim adopted grandchildren are reaped by this controller.

## Mutation results

Each mutant changed only private snapshot source using apply_patch, ran the indicated targeted control with E, then was reverted with apply_patch before the next probe. No survivors or inconclusive mutants among these three bounded changes.

- M1, receipts.py _publish_receipt: replaced publication `os.fsync(directory)` with a no-op. `E python3 -m unittest tests.test_verifier_recovery.DurableReceiptRecoveryTests.test_faults_never_leave_a_valid_pass_or_partial_receipt -v`: FAILED, exit 1, 1 test in 1.514s; directory-fsync subtest reported `AssertionError: OSError not raised`. KILLED: control detects absent directory durability.
- M2, receipts.py validate_evidence: disabled exact git_head mismatch condition. `E python3 -m unittest tests.test_verifier_recovery.DurableReceiptRecoveryTests.test_same_tree_new_head_invalidates_receipt -v`: FAILED, exit 1, 1 test in 0.424s; `AssertionError: False is not true` for expected head-staleness gap. KILLED: same-tree new HEAD cannot qualify under the tested contract.
- M3, verification.py _retain_checks: dropped completed results from cancellation exception. `E python3 -m unittest tests.test_verifier_recovery.VerifierRecoveryTests.test_node_cancellation_keeps_prior_command_failure -v`: FAILED, exit 1, 1 test in 0.301s; `AssertionError: 'incomplete' != 'fail'`. KILLED: control detects loss of original failed verdict during later cancellation.

Final `git diff --exit-code` in snapshot passed; before/after identity checks showed both candidate and restored snapshot exact original HEAD/fingerprint and clean Git status.

4. After the code reviewer reported a separate temporary-output cleanup boundary, ran `E python3 <local-path>`. Exit 0 as a reproduction script; output: `REPRODUCED: completed exit=7 and specific original output unavailable; raised temporary output close fault`. The retained script wraps real TemporaryFile context managers, closes the files, then injects OSError on context exit. Actual execute completes a subprocess printing a specific original message and exiting 7, but raises OSError without a result attribute instead of retaining ProcessResult. This independently confirms the code review finding without repeating the full suite.

## Findings, limitations and conclusion

Blocking finding P2 / AC-001: `.grok-stack/adaptive_grok/python_test_runner.py:202` and return at line 252 leave TemporaryFile context-manager cleanup outside the protected result-retention path. A completed subprocess's exit 7 and output are discarded when temporary output close raises OSError. The ordinary recovery suite remains green because its cleanup probes cover _stop and TemporaryDirectory.cleanup, not TemporaryFile.close/__exit__. Add a failing control for this actual output-file cleanup boundary (including cancellation retention), then repair result/primary exception preservation. The code reviewer reported the same implementation defect; this review independently reproduced the completed-result branch. The cancellation-close combination is reported by the code reviewer, not independently executed here.

Otherwise, tests assert retained specific original messages/output rather than merely a nonzero aggregate status. They distinguish completed check_status from gate status and cancellation terminal state, and fault controls remove both prior pass and partial publication artifacts. These are meaningful controls, but do not exhaust AC-001 cleanup boundaries.

Unexecuted: all 172 unchanged combined controls/full Core/coverage/factory PostgreSQL suite (coordinator already supplied exact-head verification; this review was expressly bounded); arbitrary crash/power-loss simulation; every instruction-level signal interleaving; all filesystem fault combinations; deployed Trust CI/holdout/human approvals; selector and issue-227/grant behavior excluded by task. Mutation coverage is the three named claims, not a blanket score. Linux descendant controls accept absent/zombie states; they prove no live owned descendant, and direct-child reaping, not reaping adopted grandchildren or children that deliberately escape the owned session. These limits do not invalidate the bounded acceptance criteria reviewed here.

Conclusive FAIL for this exact candidate snapshot and bounded test-review scope: acceptance criterion AC-001 is violated at temporary-output cleanup and no regression control detects it. Coordinator must preserve the finding and route repair before requesting renewed review; any changed candidate requires fresh identity-bound evidence. External exact-head App-owned Trust CI and required approvals remain separate.
