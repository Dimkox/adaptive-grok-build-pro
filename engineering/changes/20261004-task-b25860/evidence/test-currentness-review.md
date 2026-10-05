# Independent currentness, compatibility and import follow-up

PASS for the reviewed repair delta. The prior source-inventory and route-profile findings are closed by fresh actual CLI controls. Four change-relevant mutants were killed. The complete local verifier and exact-head App check remain required; this is test-review evidence, not a full verification or merge approval.

Route: b258608f2ced. Change: 20261004-task-b25860. Comparison base: 2a8e3839a469b3e05da167e9d8a807bf18e6adbf. Candidate: <repository-root>/.review-scratch/m8-one-task-autonomy. Before and after review: clean HEAD ccbbccc318c141b1aada9b61050cbceb7c56a4ef; fingerprint 4a4c14a0a64bbcb87a33d6ebe399108fd82faf3582f39d51352662046f3e9b0f. Earlier reports, local PASS and App FAIL retain their original identities and are historical.

reviewed-tree-modified: no

## Isolation and inspected scope

Startup measurement was recorded privately at 2026-10-05T02:01:46Z before source/route reads: 14 physical cores, 28 online logical CPUs, process affinity exposing 22, inherited cgroup cpuset 0-27, no finite actual-cgroup ancestor quota. Child-only widening verified 28 CPUs with unchanged membership/quota. Reviewer used one process on CPUs 0-3, at most four CPUs; controller affinity unchanged. Full commands/results are in the private capacity.md.

Trusted, owned, non-sticky .review-scratch parent and fresh private <repository-root>/.review-scratch/test-review-m8e-Kqseiv are mode 0700. Exact snapshot is its snapshot/ directory, created with:

`GIT_OPTIONAL_LOCKS=0 git clone --no-hardlinks <repository-root>/.review-scratch/m8-one-task-autonomy <repository-root>/.review-scratch/test-review-m8e-Kqseiv/snapshot`

Snapshot clean HEAD/fingerprint matched the candidate before testing and after restoring all mutants. Mutations used apply_patch only in private scratch. Candidate observations used GIT_OPTIONAL_LOCKS=0 and PYTHONDONTWRITEBYTECODE=1; no candidate source, index, runtime or artifacts were written.

Fully read the writer's task-1-currentness-report.md and actual f839..ccbb diff, including surrounding changed implementation/tests. Current_context now binds all Git-visible tracked/nonignored untracked bytes and modes, reads them with bounds and no-follow descriptors, refuses credential paths before opening, and rechecks inventory/HEAD. Actual route semantics supply the normalized profile; missing, malformed and unsupported risk/domain/gate inputs deny. Compatible phase/timestamp/order changes are stable. Cohort V2 has explicit version 2, floor 1 and separate digest domain; legacy V1 floor 30 and literal schema bytes remain intact. M9 runtime is unchanged and rejects V2 through its existing exact-V1 boundary. Root project-state tests bootstrap factory/src for isolated discovery. Architecture/prose/criteria/phase/lessons changes were inspected. No external authority or additional feature was introduced.

Actual base and current earned-autonomy.v1.schema.json blobs both equal dc153e0f0199e6e025769cbaeceea6b8086cc7c4.

## Fresh controls

All tests run from private snapshot. Define exact prefix E as:

`GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=factory/src:delivery/src:.:.grok-stack taskset -c 0-3 python3`

Initial command (with timeout 60 preceding python3):

`E -m unittest factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_cli_currentness_includes_root_tests_scripts_hooks_and_unknown_sources factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_cli_profile_requires_actual_compatible_route_and_stable_semantics factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_source_reader_bounds_links_and_credentials_fail_closed factory.tests.test_autonomy.OneAcceptanceFloorTests factory.tests.test_autonomy_schema.AutonomySchemaTests.test_v2_changes_only_cohort_wire_and_one_case_floor delivery.tests.test_m8_boundary.M8BoundaryTests.test_legacy_handoff_rejects_new_v2_cohort_without_widening_m9 factory.tests.test_semantic_contracts.SemanticContractTests.test_public_schemas_are_closed_bounded_and_have_exact_versions factory.tests.test_semantic_bridge.SemanticBridgeTests.test_bridge_contracts_are_closed_versioned_and_invent_no_m5_fields factory.tests.test_landing_api.LandingApiTests.test_predecessor_contract_migration_showcase_and_published_release_record_are_frozen`

Observed: exit 0, 10 tests, 4.128 s, OK. Executed claims include separate-process actual CLI root tests/scripts/hooks/unknown source changes, untracked additions, assume-unchanged, ignored artifacts, symlink refusal; absent/malformed/changed/high-risk route semantics and stable compatible metadata; reader bounds/credential refusal; V1/V2 constructors/parser/version/domain/evaluator/schema parity; exact-V1 M9 refusal; known-schema inventories and literal predecessor bytes.

Exact isolated external-failure regression:

`GIT_OPTIONAL_LOCKS=0 env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 taskset -c 0-3 python3 -I -m unittest discover -s tests -p test_project_state.py`

Observed: exit 0, 20 tests, 0.185 s, OK. No ambient PYTHONPATH or collection side effects supplied factory imports. This named-module discovery is not whole-repository discovery.

## Actual private source/schema mutants

M1 — KILLED. Added `if name.startswith('tests/'): continue` before reading files in current_context. Command: `E -m unittest factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_cli_currentness_includes_root_tests_scripts_hooks_and_unknown_sources`. Exit 1, one test, 1.571 s, one failure for tests/test_structure.py: actual CLI admission exit 0 versus expected 2. Restored afterward.

M2 — KILLED. Replaced `_route_profile(root)` with the old hardcoded low-risk profile dictionary. Command: `E -m unittest factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_cli_profile_requires_actual_compatible_route_and_stable_semantics`. Exit 1, one test, 0.425 s, failure: absent-route admission exit 0 versus expected 2. This mutant fails at the first absent-route assertion; later malformed/high-scope branches ran on intact source, not as independent mutants. Restored afterward.

M3 — KILLED. Added actual private unapproved-successor.v3.schema.json containing {}. Command: `E -m unittest factory.tests.test_semantic_contracts.SemanticContractTests.test_public_schemas_are_closed_bounded_and_have_exact_versions factory.tests.test_semantic_bridge.SemanticBridgeTests.test_bridge_contracts_are_closed_versioned_and_invent_no_m5_fields factory.tests.test_landing_api.LandingApiTests.test_predecessor_contract_migration_showcase_and_published_release_record_are_frozen`. Exit 1, three tests, 0.008 s, three failures: both exact inventories identify the unknown file; historical count changes 23→24. Deleted only that private mutant file afterward.

M4 — KILLED. Changed private literal earned-autonomy V1 floor 30→1. Command: `E -m unittest factory.tests.test_landing_api.LandingApiTests.test_predecessor_contract_migration_showcase_and_published_release_record_are_frozen`. Exit 1, one test, 0.007 s, historical digest mismatch: original 98818e23ea78821c1c602774072c77bf7d891ef69fe2ba03f0ecbad9220134fc versus d8d1f12c4ee4b729dc10a37f1cd52df0e6fce52fda52dc1d1a3853ff48ae3b20, both count 23. No normalization hides V1 drift. Restored afterward.

Restoration command: `E -m unittest factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_cli_currentness_includes_root_tests_scripts_hooks_and_unknown_sources factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_cli_profile_requires_actual_compatible_route_and_stable_semantics`. Exit 0, two tests, 3.662 s, OK. Scratch status empty and fingerprint again exact 4a4c. One intermediate combined private patch failed atomically due to hunk ordering; split patches succeeded. No candidate mutation or tool-denial retry.

## Limits and final status

Four mutants killed; none survived or was inconclusive. All bounded probes completed within 180 seconds, one process at a time. No exhaustive mutation percentage, race campaign, all-route fuzzing or atomic whole-repository snapshot against a malicious same-user writer is claimed. Existing observed-read/inventory checks and the documented limitation are appropriate.

Unexecuted: complete factory/Core/coverage/PostgreSQL/local verifier/App checks, packaging/publication and other operational acceptance. No old whole-branch or writer module suite was repeated. No subagents, secrets, providers, network or external writes. CLI remains an advisory named-action decision consumer, not command execution, external approval or empirical M7/M9 qualification. Missing-route denial in a fresh clone is intentional; normal routing must precede activation.

Currentness/profile findings closed and compatibility/import controls pass at exact ccbb/4a4c. Candidate before/after unchanged. All observations STOPPED. Coordinator must persist both selected review reports, freeze source and run fresh complete local/App gates before completion.
