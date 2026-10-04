# Bounded sandbox-capability fixture repair

Source before repair: 939bbd2701856e993641851d44ed4b8ab445d2e1.
Frozen repair HEAD: 39dd5dc72976022e25058edf3255dc210c5b0a8b.
Frozen tree fingerprint: adb42c635cb2f85f05ef7dcb09d57cf28956c6517e3b1a6d1e7c02ee2d25d27c.
Working tree: clean. Route89578a; PR242. Batch observation22:02:00–22:07:30UTC,330s.

## Failure and cause

The controller's sanitized App111536087381 job0913d153-11da-444b-97df-c85d2f1dacfd diagnostic reports repository coverage exit1 in582.633s with exactly two dispatch-inventory assertion failures; other root/TrustCI/holdout contours reportedly passed. These are historical external results, not qualification of this repair.

Both failing controls exactly reproduce when the caller supplies `GROK_VERIFY_CAPABILITY=repository-sandbox`. Production `verification._python` correctly emits its existing allowed PostgreSQL SKIP for that value; the fake local-dispatch fixture inherited it while expecting the command to execute. This investigation did not inspect runner environment, keys, credentials or a server; the controlled reproduction and source branch establish the fixture defect, not a claim of directly observed server environment.

The repair isolates only `FailFastVerificationTests.python_tree`: temporarily remove that one capability flag using the existing non-clearing environment-patch pattern, then restore it. One explicit inherited-sandbox regression asserts PG dispatch and restoration. Production code, full check inventory, environment propagation, skip allowlist and external policy are unchanged. Candidate diff:3files,+21/-1, including concise test-plan/mistake notes.

## Reproduction and bounded controls

All unittest commands use `PYTHONPATH=.grok-stack:.`, `PYTHONDONTWRITEBYTECODE=1`, `GIT_OPTIONAL_LOCKS=0`, child affinity0-3 and outer `timeout --signal=TERM --kill-after=3s 177s`; allocation at most4 CPUs from verified28. Run commands from the candidate repository.

Define the two exact targets:
```bash
first=tests.test_verification_doctor.FailFastVerificationTests.test_default_optional_skip_keeps_successful_python_inventory
second=tests.test_verification_doctor.FailFastVerificationTests.test_optional_skips_keep_success_inventory_and_keep_going_collects_failures
```

- RED before repair: `GROK_VERIFY_CAPABILITY=repository-sandbox python3 -m unittest "$first" "$second"` →2 failures in0.008s,0.460s wall; actual executed inventory ends at factory-unit rather than PostgreSQL.
- New regression RED before fixture fix: `python3 -m unittest tests.test_verification_doctor.FailFastVerificationTests.test_dispatch_fixture_isolates_and_restores_inherited_sandbox_capability` →1 failure in0.005s,0.417s wall: skip versus pass.
- GREEN sandbox: `GROK_VERIFY_CAPABILITY=repository-sandbox python3 -m unittest tests.test_verification_doctor.FailFastVerificationTests` →13 PASS,4.279s.
- GREEN ordinary: `env -u GROK_VERIFY_CAPABILITY python3 -m unittest tests.test_verification_doctor.FailFastVerificationTests` →13 PASS,4.006s.
- Existing `VerificationTests` methods `test_python_pr_requires_factory_postgres_api_and_restart_exit_runner`, `test_python_pr_skips_factory_postgres_exit_only_in_repository_sandbox`, `test_python_pr_propagates_local_factory_postgres_exit_failure`, `test_python_pr_does_not_trust_arbitrary_verifier_capability`, under inherited sandbox →4 PASS,2.706s. These retain local execution/failure, exact sandbox skip and arbitrary-capability rejection.
- `python3 -m ruff check tests/test_verification_doctor.py`, `git diff --check`, staged `git diff --cached --check` →PASS.

After commit, actual CLI observation:
```bash
GROK_VERIFY_CAPABILITY=repository-sandbox python3 scripts/grok_verify.py --mode fast --no-record --test "$first" --test "$second" --test tests.test_verification_doctor.FailFastVerificationTests.test_dispatch_fixture_isolates_and_restores_inherited_sandbox_capability --budget 30
```

PASS, process0.502s/wall0.945s; source stability PASS, terminal completed, receipt_not_recorded, scope not-run. This is a bounded observation, not full verification or scope admission.

## Handoff and limits

No full rerun, push, PR mutation, merge, deployment or verification receipt was performed by this writer. Previous local PASS/reviews are historical once this repair changes the tree; refresh affected independent reviews, persist reports, commit/freeze, then perform ONE fresh qualifying final gate under the approved delivery order. Full-suite/external qualification remains unexecuted in this writer lane. Rollback is a normal isolated-branch revert of repair39dd5dc72976022e25058edf3255dc210c5b0a8b, requiring fresh evidence.
