# Implementation controls — local, not delivery authority

Original comparison base/implementation starting HEAD: ee3911869419204154e02900e58bf31492ee744c. Isolated branch: feat/verify-fast-fail. Sole application writer: general_implementer. Full PR verification, independent reviews, final receipts and App-owned exact-head Trust CI remain coordinator work; this file claims none of them.

## Change

PR/release dispatch uses the same closed completed-status/skip policy as final QG. Primary output remains intact; later scheduled work has SKIP, command=null, empty logs and string metadata `code=not-executed-after-required-refusal`, `execution=not_executed`, `blocked_by=<actual-check>`. Source-stability and final QG always run. Valid stable refusals may record FAIL; invalid authority and source mutation remain unrecorded. Explicit keep-going collects diagnostics while architecture preflight stays closed. Ordinary fast and explicit landing behavior remain compatible, including Core measurement/export and cancellation.

Named fast smoke reuses existing Core environment/execute, requires explicit existing unittest targets and clean committed HEAD, and refuses receipt creation through the CLI's required no-record flag. Its positive 1–180 s subprocess timeout adds bounded owned-process cleanup and Git identity checks afterward; it is not a strict total wall-clock guarantee or a verification receipt. No service, cache, dependency, version/release or deployed Trust CI change.

## RED and focused GREEN

Common bounded environment: `GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.grok-stack:.`; child affinity `taskset -c 0-27`. Every covering invocation used `timeout --signal=TERM --kill-after=3s 177s`.

- RED: `python3 -m unittest tests.test_quality_gates.QualityGateTests.test_completed_refusal_does_not_require_future_checks tests.test_verification_doctor.FailFastVerificationTests tests.test_python_test_runner.NamedSmokeTests` — 7 actual dispatch failures; missing planned predicate/smoke/keep-going APIs also produced 5 errors. Ruff, pilot, Core and Factory all dispatched later commands after refusal.
- Additional RED: `python3 -m unittest tests.test_verification_doctor.FailFastVerificationTests.test_node_and_composer_refusals_stop_later_commands` — 3 Node commands dispatched when only the first refusal should execute.
- Additional compatibility RED: `python3 -m unittest tests.test_verification_doctor.FailFastVerificationTests.test_fast_authority_refusal_keeps_repository_diagnostics_compatible` — fast contract diagnostics were skipped. Minimal mode guard restored their previous execution; that control and the default optional-skip inventory control then passed (2 tests, 0.346 s).
- GREEN: original named/refusal controls plus `tests.test_quality_gates` and `tests.test_verifier_recovery.VerifierRecoveryTests` — 29 tests passed in 20.390 s.
- Broader fault investigation: five modules with eight xdist workers — 12 fixture failures, 233 passed, 42.73 s. Missing typed PR authority and lint-invalid sample fixtures had previously relied on continuation; individual diagnostic tests now request keep-going, and successful scope fixtures provide lint-valid source and real typed binding. No allowance was widened. The 14 formerly failing controls passed in 9.31 s with four workers.
- Covering GREEN: `python3 -m pytest -p xdist.plugin -p no:cacheprovider -n 8 -c /dev/null -q tests/test_verification_doctor.py tests/test_quality_gates.py tests/test_verifier_recovery.py tests/test_verification_scope.py tests/test_python_test_runner.py` — 248 tests and 386 subtests passed in 38.67 s. Later additions (fast compatibility, default optional skip and same-tree/new-HEAD smoke) are included in the committed-HEAD rerun, whose exact identity/result is returned to the coordinator.
- Real CLI controls cover Core imports, repeated explicit targets, dirty HEAD, invalid mode/no-record/empty target/budget, retained existing receipt bytes, failed assertion, timeout, source mutation and SIGTERM cancellation with before/after Git identity.
- Ruff on all four source/CLI modules and four affected test modules, and `git diff --check`, passed. Fresh committed-HEAD controls and a real named CLI invocation are required before writer handoff.

## Limitations and rollback

This is targeted local evidence only. The successful full PR/release gates may exceed 180 s; smoke, skips, cancellation and historical results do not qualify them. The integrated Core test/coverage operation finishes its existing export before outer fail-fast stops Factory/PostgreSQL; its cancellation/coverage contract is preserved. Reviewers independently probe the frozen committed candidate. Revert/forward-fix through a new gated PR; keep-going remains an explicit diagnostic fallback. No push was performed by the writer.
