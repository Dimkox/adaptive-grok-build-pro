# Output-file-close review repair: focused implementation evidence

Route c2333ca04e25; sole selected general_implementer; branch fix/v211-verifier-recovery. Repair starts from HEAD30297838c1a08a0ebe3944af07dfb69968202587, comparison base63799f8760d3a55028d83ab5ff0116ececf8f7d1, initial clean fingerprint dd55524155ae434f96e778543ca8b789caa66ac3ab6d64b121bdff379f642e16. Startup capacity was measured and recorded before inspection; assigned CPUs4,5/max2 workers are detailed in output-close-repair-capacity.md.

## Finding and bounded repair

Read both complete independent failed reports and the actual scratch probes: .review-scratch/code-review-Ls59aR/probe_cleanup.py and .review-scratch/test-review-vv1lqV/close_fault.py. Both reproduced real TemporaryFile context-exit OSError replacing a completed exit7/specific output; the code probe also reproduced lost RunCancelled. The earlier successful focused and controller full-PR results did not cover this boundary and remain historical.

Retain the computed ProcessResult before either output context exits. Each close records a bounded cleanup diagnostic without replacing that result or a primary exception; RunCancelled receives its original result and cleanup notes. Both handles are attempted even when one close fails. Check cancellation after each close to retain a first signal delivered during close. Existing consumers already fail closed on cleanup_error, so the completed exit0 remains visible while its verifier check is failed. Only runner and its recovery test module changed in this repair; the contour remains exactly five product files. Scope selector, grants, modes, factory inventory, external trust, VERSION and PROJECT_STATE are unchanged.

## Fresh RED and GREEN

Six-method command (same command before and after repair):

```bash
taskset -c 4,5 env -u GROK_TEST_WORKERS python3 -m unittest tests.test_verifier_recovery.OwnedRunnerRecoveryTests.test_output_close_keeps_completed_pass_and_failure tests.test_verifier_recovery.OwnedRunnerRecoveryTests.test_output_close_keeps_primary_cancellation_and_result tests.test_verifier_recovery.OwnedRunnerRecoveryTests.test_output_close_failure_keeps_missing_command_result tests.test_verifier_recovery.OwnedRunnerRecoveryTests.test_output_close_failure_keeps_pre_result_primary_exception tests.test_verifier_recovery.OwnedRunnerRecoveryTests.test_output_close_failure_fails_gate_with_completed_exit_visible tests.test_verifier_recovery.OwnedRunnerRecoveryTests.test_signal_during_output_close_keeps_completed_result -q
```

RED on unrepaired product: exit1;6 tests in0.789s; FAILED(errors=16). Each of16 stdout-only/stderr-only/both fault cases raised the injected close OSError instead of retaining the completed result or primary exception. An earlier test-setup run placed assertions outside subTest blocks and added secondary unbound-local errors; assertion placement was corrected before this valid RED, without changing product code.

GREEN after repair: exit0;6 tests in0.771s; OK. Assertions pin pass/fail exit0/7, exact stdout/stderr, primary cancellation exit143 and notes, missing-command exit127, pre-result primary ValueError and notes, failed gate with summary exit=0, signal during either close, and both real handles closed.

Focused relevant controls:

```bash
taskset -c 4,5 env -u GROK_TEST_WORKERS python3 -m unittest tests.test_verifier_recovery tests.test_python_test_runner.PythonTestRunnerTests.test_timeout_stops_owned_descendant_process tests.test_python_test_runner.PythonTestRunnerTests.test_controller_exit_stops_owned_descendant_process tests.test_python_test_runner.PythonTestRunnerTests.test_sigterm_cancels_owned_group_and_restores_previous_handler tests.test_python_test_runner.PythonTestRunnerTests.test_output_limit_applies_even_when_process_exits_quickly -q
```

GREEN: exit0;30 tests in13.442s; OK (26 recovery methods plus4 existing timeout/descendant/signal/output-limit controls). Fixtures select up to two workers; the unittest harness does not override their worker configuration. `taskset -c 4,5 ruff check .grok-stack/adaptive_grok/python_test_runner.py tests/test_verifier_recovery.py`: exit0, All checks passed. `taskset -c 4,5 python3 scripts/grok_spec.py validate engineering/changes/20261002-fix-verifier-lifecycle-and-cancellation-preserve-c2333c/change-spec.yaml --gate`: exit0, ok=true, errors=[], all7 entries mapped, digest1b0ad87e43a7bc6905601a3bffc369be64fded713fd0b5c85ddb786528d9cde4. `git diff --check`: exit0, no findings. Spec validation checks typed mapping, not a fresh full verification or approval.

## Exact tested bytes and preserved reports

SHA256 product inventory:

- .grok-stack/adaptive_grok/python_test_runner.py:4274083dea05f655a8d0284b685a54523491f8bb91afdd4f2612bd902b60da1c
- .grok-stack/adaptive_grok/verification.py:4bbf809cc97e628694a1cd933485eecc74d17379672b5179197b4bb4a13f2434
- .grok-stack/adaptive_grok/receipts.py:923057667277b8a31425f650bf548d6fb2d463cae3a72c2ba2d839f67d72dd2a
- scripts/grok_verify.py:b0ce3c5e371c54ac0bd041818731e644151de32f5a30abd2e402a2aae6751db2
- tests/test_verifier_recovery.py:3c134f62ef16e04c18f95eb38a5e4d220747ba2785bee6ea7d05c9d065f01163

Complete failed reports are preserved unchanged: code-review-initial-fail.md SHA256c11d9c6674ef4cf5350b407e23349d4bb1430881532fcaa5f90dcfd6e5c4814d; test-review-initial-fail.md SHA256418672a588df9aa89f56023cb5cb2802effe0ec12a3171c0603ad9bf32d27fcd. Their FAIL verdicts describe the original exact HEAD/fingerprint, not fresh review of the repaired candidate.

## Limits and controller handoff

No individual full-suite rerun, new review, external write, push, merge, deployment or release was performed by this writer. User-approved delivery topology is one combined source PR, artifact PR separate; the controller owns fresh full gate and all selected independent reviews on the exact combined HEAD, then external exact-head Trust CI/approvals. This repair evidence is focused implementation evidence only and becomes historical workflow evidence after aggregation. Final clean commit/HEAD/fingerprint are handed to the controller out-of-band.

D overlap remains bounded: early architecture-input preflight belongs inside _verification_run; record=False retains failed checks and evidence_status=not_recorded without unsafe receipt rebinding. This repair does not alter that integration boundary.
