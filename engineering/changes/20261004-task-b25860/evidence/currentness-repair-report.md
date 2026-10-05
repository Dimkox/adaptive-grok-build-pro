# M8 confirmed currentness / compatibility repair handoff

Status: DONE_WITH_CONCERNS. Sole application writer has stopped all candidate writes after this report. Independent follow-up, one fresh complete local gate, exact-head App qualification, final clone activation and delivery remain controller work; this report is bounded implementation evidence, not merge authority.

## Frozen identity and scope

- Branch: feat/m8-one-task-autonomy; route b258608f2ced; change 20261004-task-b25860.
- Parent reviewed candidate: f8393ea5ba3bd8d014e46fa947d20fd78362247d, fingerprint8dea75f544f20a45fc306af003b46019a90aa28e576116e8b8466978396827b9.
- Actual comparison base: merged PR244 2a8e3839a469b3e05da167e9d8a807bf18e6adbf; no fetch/rebase/external operations in this batch.
- Repair commit/final HEAD: ccbbccc318c141b1aada9b61050cbceb7c56a4ef.
- Final tree fingerprint: 4a4c14a0a64bbcb87a33d6ebe399108fd82faf3582f39d51352662046f3e9b0f; Git status clean before report creation. This private report is ignored workflow content, not candidate product.
- Official workflow: ready -> implementing -> verifying -> reviewing. No full verifier, full factory suite, coverage, external checks or reviewer agents launched by this writer.
- Startup measured before route/source inspection:14 physical /28 online logical CPUs; process affinity22, child-only widening probe verifies28; actual cgroup membership, mounts and ancestor cpuset/quota inspected, no finite quota found. Private snapshot recorded locally first; focused commands use affinity0-3 and aggregate ceiling12, never controller affinity changes.

Root-authorized batch repairs the three confirmed source/profile/wire findings and the additional exact App import failure. Complete triage reports were read before implementation. The prior local full PASS and external f839 App FAIL remain bound to their original head; neither is reused as fresh qualification.

## Implementation

1. `owner_autonomy.current_context` inventories all Git-visible cached and nonignored untracked paths, including root tests/scripts/hooks, configuration, prose and unknown modules. Actual bytes and file modes are hashed rather than relying on Git status; `assume-unchanged` cannot hide drift. Inventory/head are checked again after reads. Bounds:2MB path inventory,20000 files,16MiB/file,256MiB total; absent/deleted files, unsafe paths, links/nonregular files, changing read metadata and bound violations fail closed. Descriptor-relative O_NOFOLLOW reads never follow parent/leaf links. Recognized credential paths/extensions, including accidentally Git-visible *.env, deny before any open; ignored runtime/dist/private fixtures are not inventoried.
2. Actual `.grok-stack/runtime/active-route.json` is bounded and normalized: schema version, route ID, task/intent/risk, domains/task_domains, selected allowed/analysis/review/write agents, quality profiles, human gates and required evidence. Missing/malformed/unsupported inputs deny L0. Compatible medium/API/base+contracts/no-gate work retains local_read/local_test L1 only; high/security/production/unknown domain or unmet gates deny. Agent-selection consistency is validated. Array ordering, compatible workflow phase and timestamps alone do not change the profile digest; route/task/risk/domain/agent/profile/gate changes do. No fabricated current route or generic worker automation is claimed.
3. Restored legacy CohortEvidenceV1 floor30 and exact original schema bytes. CohortEvidenceV2 has schema_version2, distinct digest domain adaptive-factory.m8-cohort-evidence/v2 and additive schema URN urn:adaptive-factory:m8:earned-autonomy:v2, floor1. Constructor/parser reject zero, bool and unsupported versions; evaluator explicitly supports only the two actual cohort types. Nested tuple/task/M7 and recommendation/profile/demotion contracts remain V1, canonical blocked M7 is preserved, and M9 still accepts exact V1 only. Owner-policy path remains independent of empirical cohort recommendation.
4. Closed schema inventories name only the two explicit successors (owner V1, earned V2). Historical predecessor count23/hash98818e23ea78821c1c602774072c77bf7d891ef69fe2ba03f0ecbad9220134fc compares literal old bytes again, without floor normalization. V1 current/base blobs both dc153e0f0199e6e025769cbaeceea6b8086cc7c4; base diff for that schema is empty. Migration/showcase/old release pins unchanged.
5. Root `tests/test_project_state.py` bootstraps ROOT/factory/src explicitly, fixing isolated unittest discovery without relying on collection side effects, PYTHONPATH or installed factory distributions. Trust CI image, environment, runner and deployed policy are untouched.
6. Minimal architecture contract/path binding, AC001 V2 naming, current README/state compatibility/scope/rollout/rollback and concise root lessons were reconciled. VERSION remains2.2.0 candidate; published2.1.1 historical metadata, Liqvera immutable provenance, unknown numeric totalsnull and external trust boundaries remain unchanged.

## RED and GREEN evidence

All commands run from candidate root unless otherwise stated, with PYTHONDONTWRITEBYTECODE=1 and taskset -c0-3. Focused process budgets are <=180 seconds. Common PYTHONPATH for factory/delivery controls: factory/src:delivery/src:.:.grok-stack.

Source/profile initial RED:

`GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=factory/src:.:.grok-stack taskset -c 0-3 python3 -m unittest factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_cli_currentness_includes_root_tests_scripts_hooks_and_unknown_sources factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_cli_profile_requires_actual_compatible_route_and_stable_semantics`

Observed:2 tests/1.406s, FAILED6: all four tracked root executable mutations and an untracked unknown module were still admitted; absent route was still admitted. After production repair:2 tests/3.308s OK. The subsequently expanded controls cover assume-unchanged, ignored runtime/dist/.env fixture, unsafe source link, malformed route, every requested route semantic field, compatible reordered selections and phase/timestamp stability.

Version/compatibility RED:

`python3 -m unittest factory.tests.test_autonomy.OneAcceptanceFloorTests factory.tests.test_autonomy_schema.AutonomySchemaTests.test_v2_changes_only_cohort_wire_and_one_case_floor factory.tests.test_autonomy_schema.AutonomySchemaTests.test_schema_freezes_authority_limits_and_has_no_effect_surface`

Observed:4 tests/0.350s, FAILED4/errors1: V1 accepted minimum1/29, new V2 absent, V1 schema floor remained1. New exact-V1 M9 control separately RED with missing V2 import (1 test/0.001s). After repair, those controls plus M9 named test:5 tests/0.606s OK. An intermediate test typo `recommendation.reason` was corrected to existing `reason_code`; this was test-authoring feedback, not a production mutation claim.

Additional safe-reader RED:

`python3 -m unittest factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_source_reader_bounds_links_and_credentials_fail_closed`

Observed:1 test/0.005s FAILED for accidentally-tracked.env, intercepted attempted open before reading any credential. Minimal extension refusal repaired it. Final named reader/currentness/profile controls:3 tests/3.637s OK.

External import RED -> GREEN (exact isolated command, no ambient Python path):

`env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 taskset -c 0-3 python3 -I -m unittest discover -s tests -p test_project_state.py`

Before fix:20 tests/0.188s FAILED1, ModuleNotFoundError: adaptive_factory at the owner-policy state binding import. After bootstrap:20 tests/0.197s OK; repeated after final state/docs edits:20 tests/0.197s OK. No factory test collection or installed package was used to supply the path.

Bounded module verification (run once):

`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=factory/src:delivery/src:.:.grok-stack taskset -c 0-3 timeout 180 python3 -m unittest factory.tests.test_owner_autonomy factory.tests.test_autonomy factory.tests.test_autonomy_schema delivery.tests.test_m8_boundary`

Observed:67 tests/12.919s OK. Later safe-reader extension guard was covered by the three named controls above; no duplicate whole module run. After formatting the delivery imports, its new exact-V1/V2 boundary test again passed1/0.177s.

Exact inventory/historical controls:

`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=factory/src:.:.grok-stack taskset -c 0-3 timeout 180 python3 -m unittest factory.tests.test_semantic_contracts.SemanticContractTests.test_public_schemas_are_closed_bounded_and_have_exact_versions factory.tests.test_semantic_bridge.SemanticBridgeTests.test_bridge_contracts_are_closed_versioned_and_invent_no_m5_fields factory.tests.test_landing_api.LandingApiTests.test_predecessor_contract_migration_showcase_and_published_release_record_are_frozen`

Observed:3 tests/0.412s OK. An initial invocation from factory/ rather than repository root failed the cwd-relative migration inventory (0 rather than18); corrected command uses the original repository-root harness and passed without changing any pin.

`scripts/grok_architecture.py validate --json`: oktrue/findings[]. `diagram --check --json`: oktrue/mismatches[], all five generated views unchanged. Changed-file Ruff check initially found one preexisting import-order violation in touched delivery test; formatting-only fix applied, then all named changed Python files passed. `git diff --check` and staged `git diff --cached --check 2a8e3839a469b3e05da167e9d8a807bf18e6adbf` passed before commit.

Actual candidate read-only `current_context(Path.cwd())` passed, repository Dimkox/adaptive-grok-build-pro, profile digest90add309738d6bc18a9191212d9b5817788636754a587c140cbea0abc918c21d under the legitimate route. No candidate activation was written; controller performs it only on final frozen/merged SHA.

## Bounded mutation evidence

Private self-probe scratch: sibling `.review-scratch/m8-currentness-self-5Q3Uk6`, mode0700 under trusted mode0700 parent. This is a relevant-file copy for focused probes, not an independent complete-candidate review or fresh receipt. Candidate source was never mutated by these probes.

- Added named unapproved-successor.v1.schema.json only in scratch: all three inventory/historical controls FAILED as expected (3 tests/0.008s). Two exact inventories reported unknown filename; historical count became24, so wildcard successor admission is not allowed. KILLED.
- Removed that synthetic scratch file, then changed only scratch legacy earned V1 floor30 to1: historical frozen test FAILED (1 test/0.010s), retaining count23 but mismatched digestd8d1f12c4ee4b729dc10a37f1cd52df0e6fce52fda52dc1d1a3853ff48ae3b20. KILLED; no generic hash rebaseline.
- Actual CLI behavioral controls mutate synthetic root executable bytes/new files/route fields and restore within their isolated fixtures; they execute activation -> admission, not dataclass-only round trips. Existing lifecycle executes activate -> admit -> revoke -> L0 refusal with external_authorityfalse/ceilingL2 on representative outputs.
- No additional standalone postrepair source/profile implementation mutants, broad mutation score or independent-review PASS are claimed.

## Changed files

Production: factory/src/adaptive_factory/owner_autonomy.py; factory/src/adaptive_factory/autonomy.py; restored factory/contracts/jsonschema/earned-autonomy.v1.schema.json; new factory/contracts/jsonschema/earned-autonomy.v2.schema.json.

Controls: factory/tests/test_owner_autonomy.py, test_autonomy.py, test_autonomy_schema.py, test_semantic_contracts.py, test_semantic_bridge.py, test_landing_api.py; delivery/tests/test_m8_boundary.py; tests/test_project_state.py.

Bindings/prose/workflow: architecture/system.yaml; PROJECT_STATE.json; README.md; decisions.md; mistakes.md; active package architecture.md, requirements.md, change-spec.yaml, state.json. No generated diagram edits, dependency/service additions, secret reads, provider calls, Git fetch/push, release writes, Trust CI changes or M9 runtime edits.

## Rollback and concerns

Revoke clone-local activation and disable the checked-in owner policy through a separately reviewed change; do not remove revocation tombstones to resurrect authority. Source/route changes naturally invalidate old activation. Cohort V2 is explicit opt-in and cannot enter M9's unchanged V1 handoff; legacy V1 consumers retain their prior floor30.

Current bounded evidence does not qualify delivery. Fresh independent reviews, complete local verifier and exact-head App check are mandatory, especially because old local PASS/App FAIL belonged to f839 and selected modules are not the full factory exit. Controller must activate against exact final source after report freeze and again if merged SHA changes; writer intentionally did not create deployment/runtime acceptance.

The inventory intentionally binds all Git-visible bytes, including prose, so any such edit requires new activation; ignored files are outside that declared source binding. Descriptor-relative regular-file reads reject observed per-file races and inventory/head changes, but do not claim an OS-enforced atomic whole-repository snapshot against a malicious same-user concurrent writer. Linux O_NOFOLLOW behavior and current existing runtime platform constraints remain; no new cross-platform operational qualification is asserted. Numeric accounting remains unknown/null and owner confirmation remains local user authority, never an external signed Trust CI approval.
