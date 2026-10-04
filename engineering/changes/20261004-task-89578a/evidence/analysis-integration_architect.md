# Integration architect — read-only analysis

Use existing CheckResult.status=skip, command=None, empty logs and string details code=not-executed-after-required-refusal, execution=not_executed, blocked_by=actual-check. Retain actual refusal separately. Synthetic failed discovery falsely implies execution: quality_gates.py:112 and tests/test_quality_gates.py:51.

Report/v1 strict outer/reference fields remain unchanged; CheckResult.details verification.py:53 and artifact.details receipts.py:245 accept this metadata. CLI49 prints summaries/details. Do not expand strict reference/wrapper.

Early predicate inspects completed failures, unknown status and disallowed skip via existing closed QG allowance64. Full gate on partial schedule incorrectly reports future names missing105. Final QG completeness can pass despite executed test failure, so aggregate actual failure remains required. Preserve exact allowed Bandit/docs/pytest/sandbox omissions; missing/unknown/disallowed evidence fails.

PR/release-only default preserves fast/explicit landing. test_verifier_recovery.py:122 expects fast npm-test cancellation after npm-lint failure;139 retains Core failure when coverage cancels. Do not alter integrated Core/cancellation behavior.

Finalizer source-stability/fullQG verification.py:2201 always runs. Early aggregate/check FAIL has terminal completed; real cancellation keeps signal/terminal/output semantics2044. Architecture2131, governance and source mutation2253 preserve receipt refusal; stable bindable failures publish FAIL, never satisfy admission receipts.py:948.

Executed read-only controls: nine test_quality_gates tests PASS0.003s; two durable report controls (mixed failed/cancelled/skipped and closed reference/envelope) PASS1.633s. One worker CPU0, bytecode disabled; private fixtures .review-scratch/integration-analysis.c5Je2v. Capacity snapshot there recorded14physical/28logical, child0–27, no finite observed ancestor quota. No full suite/candidate/deployed changes.
