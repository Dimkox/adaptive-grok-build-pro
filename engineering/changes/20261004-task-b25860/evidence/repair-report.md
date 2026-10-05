# Bounded M8 independent-review follow-up

Status: DONE. Sole application writer stopped all candidate writes after this private report.

Route b258608f2ced, change20261004-task-b25860, branch feat/m8-one-task-autonomy. Actual merged comparison base2a8e3839a469b3e05da167e9d8a807bf18e6adbf. Starting reviewed HEAD1861e28c8108708f9e85f6e6e78df767f6eb8fa9. Repair commit822a3021c383fc0ddd2a2385790bb68d73beb4be. Clean tree fingerprint ecc7b642695c4cd878db8269b6394d7d9faceb000b6dd073db5f7959bf8e2c8b. Original implementation commit945b9127/report remains historical after base normalization and this repair.

## Changes and root cause

- Initial qualification now has a fresh runtime/no activation record for each wrong product_repository, product_source_sha and factory_source_sha. Each assertion requires denied/L0 and exact reasonprovenance_mismatch, plus no artifact. The previous tests changed a case after activation and were masked by later case_digest refusal.
- Representative activate, admit, status, external-action denial and revoke results explicitly require external_authorityFalse and authority_ceilingL2. Actual separate-process CLI fixture outputs assert those fields as well; the prior tests asserted only allowed/level and missed output-contract mutations.
- OwnerActivationV1 compares positive expires_at-issued_at duration against one hour, preserving the exact lifetime ceiling without adding to a possibly maximum datetime. A persisted extreme-future record now reaches the actual admission consumer and returns structured denied/L0/activation_expired instead of uncaught overflow.
- Only the synthetic subprocess CLI checkout gets a dynamic now+one-day expiry. Production policy expiry2026-11-04 and fixed-clock expiry controls remain untouched.
- Short lessons added to decisions.md/mistakes.md. Official phase transitions reviewing→implementing→verifying→reviewing recorded reasons explicitly stating final full verification remains pending.

Exactly five committed files: factory/src/adaptive_factory/owner_autonomy.py, factory/tests/test_owner_autonomy.py, decisions.md, mistakes.md, engineering/changes/20261004-task-b25860/state.json. No schema/production policy/new feature or architecture expansion.

## RED/GREEN

Prefix E: GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=factory/src:.:.grok-stack taskset -c 0-3 python3.

RED command: E -m unittest factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_persisted_extreme_future_dates_deny_l0_without_datetime_overflow

Observed Ran1test in0.008s; FAILED(errors=1). Traceback ended OverflowError: date value out of range at issued_at+timedelta(hours=1), reproducing the reviewed defect through persisted admission input.

GREEN command after minimal repair: E -m unittest factory.tests.test_owner_autonomy

Observed Ran13tests in1.510s; OK. Existing lifecycle, current binding/expiry/revocation, typed schema and new regression controls all passed. This is focused observation, not the final qualifying receipt.

Whitespace: git diff --check and git diff --cached --check emitted no errors; staged check preceded commit. git status --short was empty after commit. Final HEAD/fingerprint above were observed after commit.

## Previously surviving mutations now caught

Each probe ran in a separate bounded private child process using only in-memory module replacement; candidate bytes were never edited or restored. E -c loaded actual owner module text and exec-compiled a single replacement into that child's module dictionary, then ran exactly the named checked-in test. No extra test suite or reviewer/agent was launched.

Exact probe1 code:

```python
from pathlib import Path
import unittest
from adaptive_factory import owner_autonomy as owner
task_source = Path(owner.__file__).read_text()
old = "if (policy.product_repository, policy.product_source_sha, policy.factory_source_sha) != ("
new = "if False and (policy.product_repository, policy.product_source_sha, policy.factory_source_sha) != ("
assert old in task_source
exec(compile(task_source.replace(old, new), owner.__file__, "exec"), owner.__dict__)
result = unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromName(
    "factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_initial_activation_refuses_each_wrong_provenance_without_existing_record"))
raise SystemExit(not result.wasSuccessful())
```

Observed exit1; Ran1test in0.015s; FAILED(failures=3), one for each independent fresh-runtime provenance subtest: actual(True,L1,active) versus expected(False,L0,provenance_mismatch). Mutant killed.

Probe2 used the same E -c structure with replacement `"external_authority": False`→`"external_authority": True` and the single named test `factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_one_case_qualifies_activates_and_real_consumer_admits_local_test`. Observed exit1; Ran1test in0.006s; FAILED(failures=1), True is not False at activate's explicit authority assertion. This test consumes the decision output directly and does not invoke the separately changed profile definition; _decision mutant killed. These writer observations supplement, not replace, independent reviewer follow-up.

## Capacity, omissions and handoff

New startup measurement2026-10-05T00:34:25Z preceded route/source reads and was recorded privately:14physical/28online logical CPUs, inherited actual-cgroup cpuset0-27 and no finite ancestor quota; process22affinity0,1,8-27; child-only probe confirms28 without controller mutation. Focused commands used one process on0-3, below allocated ceiling12. No remote fetch, push, provider/network/production operation, full verifier, coverage, PostgreSQL, new analysis or subagent.

The only production behavior repair is overflow-safe duration validation. Local L1 reads/tests, L2 ceiling, fixed production expiry and all external boundaries remain intact. Existing initial reviewer evidence is historical at1861e28; selected reviewers must independently follow up on this committed repair before the controller freezes complete reports and invokes the single final whole-repository qualifying gate. No new receipt/external-check/merge-completion claim is made. Rollback is the existing per-clone revoke command or ordinary reviewed source revert.
