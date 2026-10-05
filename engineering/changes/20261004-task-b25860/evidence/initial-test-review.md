# Independent test review — initial candidate

Recommendation: HOLD / FAIL for the two concrete P2 regression-coverage findings below, pending the coordinator's already-selected sole-writer repair and bounded exact-head follow-up. The current implementation passes direct provenance and authority probes; these findings concern missing automated guards, not observed authorization defects. No blanket mutation-score requirement is imposed. This report does not establish full verification, merge eligibility, publication or deployed activation.

Route b258608f2ced; change 20261004-task-b25860; agreed comparison base 2a8e3839a469b3e05da167e9d8a807bf18e6adbf. Reviewed candidate <repository-root>/.review-scratch/m8-one-task-autonomy, HEAD 1861e28c8108708f9e85f6e6e78df767f6eb8fa9, tree fingerprint b4e616f01a67b4fb83dc4e38a50d378e0a9140273b5ca5e5a73e39327609f183. Before and after review, HEAD and fingerprint exactly match, and git status --porcelain=v1 is empty.

reviewed-tree-modified: no

## Isolation, resource evidence and scope

Startup CPU discovery was recorded before route/source inspection in private capacity.md. Host 14 physical cores/28 online logical CPUs; process affinity exposed22, inherited cpuset0-27, no finite actual-cgroup ancestor quota. Child-only widening to0-27 succeeded with28 CPUs and unchanged cgroup/quota. Trusted non-sticky parent <repository-root>/.review-scratch is owned by pall and mode0700; fresh private parent <repository-root>/.review-scratch/test-review-m8a-o2UkUv is likewise0700. One test process at a time, taskset0-3, allocation at most4 CPUs; no subagents, provider/network operations, secrets, production writes, full verifier, full discovery or coverage.

Scratch snapshot <repository-root>/.review-scratch/test-review-m8a-o2UkUv/snapshot was created with `GIT_OPTIONAL_LOCKS=0 git clone --no-hardlinks <repository-root>/.review-scratch/m8-one-task-autonomy <repository-root>/.review-scratch/test-review-m8a-o2UkUv/snapshot`. It reproduced clean HEAD and fingerprint exactly before testing and after restoration of every mutant. Candidate observations used GIT_OPTIONAL_LOCKS=0 and PYTHONDONTWRITEBYTECODE=1. Mutations used apply_patch only in this owned scratch. Scratch origin URL was changed locally to the actual repository ID solely for the real offline CLI probe; no network operation occurred. Ignored scratch-local activation/revocation records were produced only there.

Read actual full39-file diff and surrounding owner runtime/CLI/schema, autonomy constructor/parser/schema, state/history/package/deploy/architecture tests, plus requirements, architecture, tasks, controller analysis, implementation report and other active package evidence. Read AGENTS, selected test_reviewer prompt/configuration, adaptive-delivery, verification-evidence and verification-before-completion instructions. Controller owns the final full qualifying gate after reports freeze; no preliminary full run or review receipt was created here.

## Findings

P2 F1 — initial activation provenance refusal is not enforced by checked-in tests (`factory/tests/test_owner_autonomy.py`, current binding test near54-63; `owner_autonomy.py` qualify provenance guard near208). Removing the product repository/source/factory tuple comparison survives all11 owner tests. The existing changed factory-source case is tested only after activation, where case_digest binding independently rejects it; therefore that test cannot detect loss of qualification provenance. Reviewer direct initial activation probes on intact source deny wrong product_repository, product_source_sha and factory_source_sha with provenance_mismatch/L0. The same probe on the mutant admits wrong/product atL1. Add fresh-runtime initial-activation refusal subtests for all three fields, with matching current context.

P2 F2 — no checked-in owner test asserts decision external_authority or authority_ceiling (`factory/tests/test_owner_autonomy.py`; `_decision` near194). Changing `_decision` from external_authority=False toTrue survives all11 owner tests, despite violating the explicit no-external-authority output invariant. Intact real CLI results have False and L2; action allowlist also denies merge/provider calls. Assert external_authority isFalse and ceilingL2 for allowed, denied and revoked decisions and actual CLI output. This is a wire-contract regression gap, not evidence that current code grants an external action.

Residual limitation: actual CLI lifecycle test uses wall-clock datetime.now with checked-in policy expiry2026-11-04. Its synthetic checkout activation will fail after that date independently of implementation correctness. Reviewer shares code-reviewer's observation; deterministic future-valid fixture expiry or injected clock is a useful follow-up. Operational policy expiry itself is intentional.

## Fresh controls: claim, exact command, observed output

All commands below run from the scratch snapshot unless stated otherwise. Prefix E means the exact shell environment and executable prefix `GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=factory/src:.:.grok-stack taskset -c 0-3 python3`; this definition is part of each command, not an omitted environment assumption.

1. One/zero constructor/parser threshold, canonical schema floor, actual separate-process CLI/currentness/revocation, malformed authority/activation, explicit readiness, current/published/historical state identity, version, dist-only release helper and immutable historical bytes:

`E -m unittest factory.tests.test_autonomy.OneAcceptanceFloorTests factory.tests.test_autonomy_schema.AutonomySchemaTests.test_schema_freezes_authority_limits_and_has_no_effect_surface factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_cli_full_lifecycle_rechecks_actual_current_source_and_missing_inputs factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_each_admission_rechecks_every_binding_and_expiry factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_state_adapter_requires_explicit_readiness_and_real_provenance factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_closed_contracts_and_authority_escalation_fail factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_activation_schema_and_runtime_deny_extra_keys_and_level_escalation factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_revocation_survives_restart_and_prevents_reactivation tests.test_project_state.ProjectStateTests.test_current_owner_policy_is_bound_to_one_real_case_without_numeric_telemetry tests.test_project_state.ProjectStateTests.test_current_published_v211_binds_observed_remote_release tests.test_project_state.ProjectStateTests.test_historical_cleanup_continuation_preserves_exact_dependency tests.test_structure.StructureTests.test_version_identity_matches_readme tests.test_deploy.DeployTests.test_human_commands_tag_exact_head_without_pushing_main tests.test_manifest_package.PackageTests.test_published_zip_matches_immutable_release_record_and_embedded_manifest tests.test_history.HistoryTests.test_issue_73_historical_probe_evidence_remains_byte_identical`

Observed exit0,15tests,1.189s,OK. These are named controls selected for concrete claims; writer's entire85-test suite was not repeated.

2. Actual CLI in exact private source checkout, rather than only a synthetic miniature fixture:

`GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 taskset -c 0-3 python3 <repository-root>/.review-scratch/test-review-m8a-o2UkUv/cli_probe.py`

The checked-in private script invokes `python3 <scratch>/scripts/grok_m8.py` for status, activate, admit --action local_read, admit --action local_test, admit --action merge, revoke and admit --action local_test, asserting exact exit codes, external_authorityFalse and correspondingL1/L0. Observed respectively exit2 activation_missingL0; exit0 activeL1; exit0 admittedL1 twice; exit2 action_not_authorizedL0; exit0 revokedL0; exit2 revokedL0. All decision external_authorityFalse, authority_ceilingL2. This proves local persistence and consumer use only; no arbitrary command or external action was executed.

3. Architecture schema/inventory bindings and unchanged canonical M7 blocked semantics:

`E -m unittest tests.test_architecture_model.ArchitectureModelTests.test_seed_architecture_models_current_boundaries_and_real_contracts tests.test_architecture_model.ArchitectureModelTests.test_factory_execution_contract_inventory_is_exact_and_self_comparable factory.tests.test_autonomy.AutonomyRegressionBoundaryTests.test_exact_threshold_metrics_remain_integer_and_m7_blocked`

Observed exit0,3tests,0.582s,OK. `GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 taskset -c 0-3 python3 scripts/grok_architecture.py validate --json`: findings[],oktrue. Same prefix `scripts/grok_architecture.py diagram --check --json`: checkedtrue,mismatches[],oktrue. Actual base..HEAD `git diff --check` emitted no whitespace errors.

4. Reviewer independent provenance qualification:

`GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=factory/src taskset -c 0-3 python3 <repository-root>/.review-scratch/test-review-m8a-o2UkUv/provenance_probe.py`

Intact source: wrong product_repository, product_source_sha and factory_source_sha each returned allowedFalse,reasonprovenance_mismatch,levelL0,external_authorityFalse; exit0. Mutated guard: wrong/product returned allowedTrue/active/L1 and the independent assertion failed, exit1. This independently kills F1's mutant but is not yet a checked-in regression.

## Source mutation outcomes

M1 KILLED: change CohortEvidenceV1.__post_init__ minimum floor1→0, retain parserfloor1. `E -m unittest factory.tests.test_autonomy.OneAcceptanceFloorTests`:1test,exit1,FAIL `ContractError not raised` for replace(cohort,minimum_human_acceptances=0). Restored afterward.

M2 KILLED: change earned-autonomy schema minimum_human_acceptances minimum1→0. `E -m unittest factory.tests.test_autonomy_schema.AutonomySchemaTests.test_schema_freezes_authority_limits_and_has_no_effect_surface`:1test,exit1,FAIL0!=1. Restored afterward.

M3 SURVIVED checked-in tests, KILLED independent private probe: add `False and` to qualify provenance tuple guard. `E -m unittest factory.tests.test_owner_autonomy`:11tests,1.256s,exit0,OK. Private provenance_probe.py exit1 as above. Concrete findingF1; restored afterward.

M4 KILLED: add `False and` to status actual!=expected binding comparison. `E -m unittest factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_each_admission_rechecks_every_binding_and_expiry factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_cli_full_lifecycle_rechecks_actual_current_source_and_missing_inputs`:2tests,exit1,5failures. Source/profile/repository-binding mismatch and changed policy incorrectly admitted; real CLI source mutation returnedadmitted instead ofbinding_mismatch. Restored afterward.

M5 KILLED: early returnFalse from _revoked. `E -m unittest factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_revocation_survives_restart_and_prevents_reactivation factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_cli_full_lifecycle_rechecks_actual_current_source_and_missing_inputs`:2tests,exit1,2failures active/admitted!=revoked. Restored afterward.

M6 SURVIVED: _decision external_authorityFalse→True. `E -m unittest factory.tests.test_owner_autonomy`:11tests,1.407s,exit0,OK. Concrete findingF2; restored afterward. Independent real CLI output already assertedFalse on intact source; no current authority defect claimed.

Restoration control: scratch status empty; fingerprint againb4e616f01a67b4fb83dc4e38a50d378e0a9140273b5ca5e5a73e39327609f183. `E -m unittest factory.tests.test_autonomy.OneAcceptanceFloorTests factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_each_admission_rechecks_every_binding_and_expiry factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_revocation_survives_restart_and_prevents_reactivation`:3tests,0.032s,exit0,OK. An intermediate private multi-hunk mutation patch failed context matching without changing source; subsequent separate patches succeeded. No candidate operation was denied or repeated.

## Unexecuted / declined to judge

Full repository verification, coverage, PostgreSQL, external Trust CI and release packaging/publication: intentionally unexecuted; coordinator's one final report-containing full gate and exact-head external gate remain required. No prior evidence reused as fresh PASS. Human owner confirmation is accepted as authorized factual scope; review does not independently measure unavailable cost/intervention totals, prove empirical M7 acceptance, generalM9 operational qualification, provider deployment or factory publication. Unknown numeric totals remainnull in executed state controls. No exhaustive OS race/malformed input campaign, blanket mutation percentage, empirical telemetry or signed security approval is claimed.

After sole-writer fixes, bounded exact-head follow-up should specifically rerun new initial-provenance/authority/date controls and former surviving mutants, bind new candidate identity, and update final recommendation. Other initial observations remain historical at their recorded exact identity; they do not become fresh verification on the successor.
