# Independent code/spec/security follow-up — PASS

Route b258608f2ced; change20261004-task-b25860. This is a bounded review of exactly `1861e28c8108708f9e85f6e6e78df767f6eb8fa9..822a3021c383fc0ddd2a2385790bb68d73beb4be`, not a repeated whole-branch review. Original complete review remains historical at its original HEAD/fingerprint in `<repository-root>/.review-scratch/code-review-9ZBmhA/code-review.md`. Its observations are not relabeled fresh. Read the complete repair report at candidate `.superpowers/sdd/tasks/task-1-fix-report.md` and actual five-file delta.

## Identity and isolation

Candidate `<repository-root>/.review-scratch/m8-one-task-autonomy`; agreed PR base remains `2a8e3839a469b3e05da167e9d8a807bf18e6adbf`.

Before and after candidate HEAD: `822a3021c383fc0ddd2a2385790bb68d73beb4be`.

Before and after candidate fingerprint: `ecc7b642695c4cd878db8269b6394d7d9faceb000b6dd073db5f7959bf8e2c8b`.

Before/after `git status --porcelain=v1`: empty. Candidate commands used `GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1`; no candidate source, runtime, bytecode, index, branch or HEAD write.

Fresh exact scratch snapshot: `<repository-root>/.review-scratch/code-followup-cvrkMk/repo`, created using `git clone --quiet --no-hardlinks <repository-root>/.review-scratch/m8-one-task-autonomy <repository-root>/.review-scratch/code-followup-cvrkMk/repo`. Clean candidate required no dirty overlay; clone HEAD/fingerprint matched the above. Scratch origin locally set to `https://github.com/Dimkox/adaptive-grok-build-pro.git` solely for offline CLI identity checks; no network request. Trusted `.review-scratch` parent and reviewer directory are ownedpall/mode0700/non-sticky. Snapshot writes, test artifacts and mutation probes were confined to this private copy.

reviewed-tree-modified: no

Fresh startup discovery was recorded in `capacity.md` before route/source inspection, 2026-10-05T00:38:51Z:14physical/28online logical CPUs0-27, process22/affinity0,1,8-27; actual session2050 cgroup and user1000/user.slice ancestors have unlimited cpu.max with inherited effectivecpuset0-27. Child-only widening verified28 and same cgroup bounds. Reviewer tests ran one process at a time pinned0-3, no agents/full verification.

## Delta judgment

The only production-code change replaces adding one hour to issued_at with comparing the positive expires_at-issued_at duration. This prevents the reproduced maximum-date overflow and preserves finite one-hour ceiling. There is no policy, schema, action allowlist, authority, M7 or M9 change. Production policy expiry remains2026-11-04.

New tests exercise persisted consumer input, fresh runtime initial provenance refusal and explicit external_authorityfalse/ceilingL2 outputs. Dynamic future expiry is limited to the synthetic CLI checkout; it does not extend checked-in owner policy. The previous two minor code-review findings are resolved by the reviewed delta. Lessons and workflow phase history accurately record focused observations and pending final whole-repository gate.

No new critical, important or minor finding from this bounded follow-up. Test reviewer independently owns rerunning the previously surviving provenance/authority mutants; their results are not asserted here.

## Commands and fresh results

All commands below ran inside the fresh private clone with `GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1`, unless explicitly identified as candidate observations.

1. `python3 scripts/grok_m8.py activate` — exit0; JSON allowedtrue,levelL1,reasonactive,authority_ceilingL2,external_authorityfalse. This created a real local ignored activation with exact clone/source/case/profile/policy bindings.

2. Using apply_patch only on private activation.json, preserve all bindings and change issued_at to `9999-12-31T23:00:00Z`, expires_at to `9999-12-31T23:59:59.999999Z`. Then `python3 scripts/grok_m8.py admit --action local_test` — exit2; JSON `{"allowed":false,"authority_ceiling":"L2","external_authority":false,"level":"L0","reason":"activation_expired","schema_version":1}`. No traceback. Former extreme-date input survivor is now rejected through the actual separate-process CLI.

3. `PYTHONPATH=factory/src:.:.grok-stack taskset -c 0-3 python3 -m unittest factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_persisted_extreme_future_dates_deny_l0_without_datetime_overflow factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_cli_full_lifecycle_rechecks_actual_current_source_and_missing_inputs` — exit0, Ran2tests in1.222s, OK. The second test freshly checks the altered dynamic synthetic policy fixture and explicit output authority assertions across separate CLI processes; this does not repeat the complete owner/writer suite.

4. Duration equivalence probe:

```bash
PYTHONPATH=factory/src taskset -c 0-3 python3 -c 'from adaptive_factory.owner_autonomy import OwnerActivationV1; from adaptive_factory.contracts import ContractError; from datetime import datetime,timezone,timedelta; from dataclasses import replace; start=datetime(2026,10,5,tzinfo=timezone.utc); value=OwnerActivationV1(1,"a"*64,"b"*64,"Dimkox/adaptive-grok-build-pro","c"*64,"d"*64,"e"*64,"L1",start,start+timedelta(hours=1)); print("exact one hour accepted"); cases=[0,-1,3601]; results=[]
for seconds in cases:
 try: replace(value,expires_at=start+timedelta(seconds=seconds)); results.append(False)
 except ContractError: results.append(True)
print("zero, negative, over-one-hour rejected:",results); assert all(results)'
```

Observed exit0: `exact one hour accepted`; `zero, negative, over-one-hour rejected: [True, True, True]`.

5. Isolated source mutant: revert only new duration comparison to former `self.issued_at < self.expires_at <= self.issued_at + timedelta(hours=1)` with apply_patch in scratch. Run `PYTHONPATH=factory/src:.:.grok-stack taskset -c 0-3 python3 -m unittest factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_persisted_extreme_future_dates_deny_l0_without_datetime_overflow`. Observed exit1; Ran1test in0.009s, FAILED(errors=1), OverflowError at owner_autonomy.py:190 through persisted `admit`. Outcome: killed. Restored current comparison using apply_patch; `git diff --exit-code` then exited0. No surviving or inconclusive source mutant in this follow-up; no overall mutation-score claim.

6. Read-only candidate final identity commands: `git rev-parse HEAD`; `git status --porcelain=v1`; `PYTHONPATH=.grok-stack python3 -c 'from pathlib import Path; from adaptive_grok.util import tree_fingerprint; print(tree_fingerprint(Path.cwd()))'` — exact identities above, clean status. `git diff 1861e28c8108708f9e85f6e6e78df767f6eb8fa9..HEAD --check` exited0.

## Remaining limits / declined to judge

- Whole-branch historical review remains bound to1861e28 and its own fingerprint. Only this five-file repair delta and listed probes are freshly reviewed at822a302.
- Full verifier, coverage, PostgreSQL, external Trust CI, packaging, publication, merge and actual candidate activation are controller-owned, unexecuted by this reviewer and not claimed passing.
- Initial-provenance and external-authority mutant adequacy follow-up is assigned to independent test reviewer; statically reviewed new assertions here without duplicating that mutation wave.
- Future wall-clock simulation beyond production policy expiration was not performed. Static diff proves only synthetic CLI fixture receives now+one-day expiry; production policy byte change is absent.
- Concurrent hostile filesystem races, malicious same-user source/state tampering and exhaustive datetime/JSON/resource-exhaustion cases were not executed; no new claim of OS isolation or external authority.

PASS for this bounded repair follow-up. Previous minor findings are resolved; readiness for merge/publication still requires coordinator final report-containing local gate and required independent exact-head external authority.
