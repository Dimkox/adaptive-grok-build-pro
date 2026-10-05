# Independent code review — accepted Liqvera M8 case

Public path projection: only the host-local absolute repository prefix is replaced with `<repository-root>`; the complete original is retained in private scratch. Exact SHAs, fingerprints, repository-relative scratch paths, remaining command arguments, findings and results are unchanged.

Selected code_reviewer, route 4e78915ad1ab, change 20261004-task-4e7891. Result: PASS within this documentation/state scope; no blocking findings. This is independent local review evidence, not runtime qualification, merge authority or external Trust CI.

## Exact source and isolation

Candidate: <repository-root>/.review-scratch/m8-liqvera-accepted. Comparison base f97966c4173fff9a3954389498568038dc57776b. Before and after HEAD 048305111df9177e2d873cf5871e8c51a64a12e1; before and after tree fingerprint 7cacbd28151987019b7fabc5453f4b1843cf9119aa76bb8ced0c86437463e55d. `GIT_OPTIONAL_LOCKS=0 git status --porcelain=v1` was empty before and after. Candidate source was clean, so exact local clone includes the complete snapshot, including existing change-package reports. `git clone --quiet --no-hardlinks <candidate> <scratch>/source` reproduced exact HEAD and fingerprint before testing.

Private scratch: <repository-root>/.review-scratch/code-m8-private.tktD2H/source. Parent .review-scratch and private scratch directory both mode 0700, owned by pall, non-sticky. Mutations only in this separate clone. No candidate writes, index refresh, bytecode, provider, credential, external Git or full verifier operations.

reviewed-tree-modified: no

## Resource startup

Recorded privately in ../cpu.md before source inspection. At 2026-10-04T23:27:41Z, `lscpu -p=CORE,SOCKET,ONLINE`, `nproc --all`, `nproc`, `taskset -pc $$`, `/proc/self/cgroup`, `/proc/self/mountinfo` and cgroup ancestor reads showed 14 physical cores, 28 online logical CPUs, default allowed affinity 0,1,8-27/capacity22. Actual cgroup /user.slice/user-1000.slice/session-2050.scope on cgroup2 /sys/fs/cgroup; session/user ancestors cpu.max=max 100000, root has no cpu.max, effective ancestor cpuset0-27. Child-only `taskset -c 0-27 bash -c 'taskset -pc $$; nproc; cat /sys/fs/cgroup/cpu.max'` confirmed affinity0-27/nproc28; its root cpu.max read was absent, resolved by actual ancestor inspection. No finite quota found; verified capacity28, one review test process. Controller affinity unchanged.

## Reviewed claims and findings

Read exact base..HEAD diff and surrounding project-state tests, current README/START_HERE/roadmap handoff, scoped brief/requirements/change-spec, controller synthesis and implementation report. The seven product paths plus active workflow package agree with AC-001 through AC-004: M8 has a separate completed_product_case.status=DONE; observed main and released source are distinct; explicit_owner_confirmation is distinguished from independent_runtime_telemetry=false; four accepted-product dependencies are enumerated and six technical prerequisite categories retained.

Accepted external product qualification points at this case. Current handoff no longer requires a duplicate first pilot. Old next_external_pilot is visibly historical_superseded and retains its original false maintainer acceptance and all original values. Historical M8 axes remain intact. No runtime/contracts/flags/VERSION/release bytes changed. Existing false boundaries for cohort, activation, general M9 operational qualification, publication and cost/intervention accounting remain binding. User-confirmed acceptance is the authority for the recorded outcome; released provenance corroborates its factory source identity rather than establishing a measured task cohort.

The implementation report identifies its own earlier checkpoint/fingerprint as historical implementation evidence and explicitly assigns later freeze/report persistence to the coordinator; this review binds the supplied later exact HEAD. No stale implementation checkpoint was treated as current review identity.

## Executed checks

All Python commands used `GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1`. Identity command: `python3 -c 'import sys; from pathlib import Path; sys.path.insert(0,".grok-stack"); from adaptive_grok.util import tree_fingerprint; print(tree_fingerprint(Path.cwd()))'`. Candidate before/after and unmodified private source printed the exact fingerprint above; `git rev-parse HEAD` printed exact HEAD above.

In private source: `taskset -c 0-27 python3 -m unittest tests.test_structure tests.test_project_state tests.test_manifest_package tests.test_workflow_sources tests.test_repo_router`: PASS, 153 tests, 23.091s, OK. `git diff --check f97966c4173fff9a3954389498568038dc57776b..HEAD`: exit0, no output.

Read-only historical preservation probe on candidate: load base PROJECT_STATE via `git show f97966c4173fff9a3954389498568038dc57776b:PROJECT_STATE.json`; load current JSON; assert equality of every original milestone axis, every original next_external_pilot field, and published_release/prior_published_releases/runtime_observations/current_continuation. Exit0: `Historical milestone axes, all old pilot fields, published releases, runtime observations and current continuation unchanged`.

Read-only `rg -n 'PROJECT_STATE' factory/src engineering/contracts pilot --glob '*.py' --glob '*.json'` found no references. Diff inventory inspection confirms this is a state/prose correction, not executable autonomy activation.

## Mutation probes

M1, accepted-result regression: private PROJECT_STATE completed_product_case.status DONE→PENDING. Exact command `python3 -m unittest tests.test_project_state.ProjectStateTests.test_m8_completed_liqvera_case_unblocks_only_accepted_product_dependencies`: exit1, one test, `AssertionError: 'PENDING' != 'DONE'` at line118. KILLED. Restored only private mutant using apply_patch.

M2, authority-boundary regression: private operational_qualification.m8_activation false→true. Exact command `python3 -m unittest tests.test_project_state.ProjectStateTests.test_runtime_observations_are_source_bound_without_promoting_qualification`: exit1, one test, `AssertionError: True is not false` at line1003. KILLED. Restored only private mutant using apply_patch.

No surviving or inconclusive executed mutants. These two probes establish only their named regression sensitivity, not a blanket mutation score.

## Unexecuted and declined-to-judge claims

Did not independently contact Liqvera GitHub/demo or re-download release ZIP; remote source hashes/release chronology are assessed for consistent transcription from supplied controller research, not independently re-observed by this reviewer. Did not execute the demo, verify full F7, measure cost/intervention data or task cohort, activate M8, deploy M9, exercise recovery or infer factory-runtime publication. Those claims are excluded or explicitly unestablished in this change. Did not run full grok_verify, external Trust CI or approval checks: the coordinator's final report-containing tree requires fresh verification and external exact-head gates. No review of unchanged runtime correctness beyond the stated authority boundary is implied.
