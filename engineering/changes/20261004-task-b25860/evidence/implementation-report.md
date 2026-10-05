# Task 1 implementation report

Status: DONE_WITH_CONCERNS. Application/source writes stopped after this private report.

Route: b258608f2ced; change: 20261004-task-b25860; selected write owner: general_implementer. Branch: feat/m8-one-task-autonomy. Accepted-case parent: 82d0b16f822256758f0773ca04e9dc74b1f06b15; planning HEAD: 1132b0411bbac058941bc7ae48b97d5196c8aeb6. Implementation commit: 945b912753dc432d3fc95f79db5f7c0cfa28d8b9. Clean candidate fingerprint from adaptive_grok.util.tree_fingerprint: f1ff3782a64b9df0dd7f3a2f810fcd5ad65148ddfa6b00db7a48cacd9c7abc6c. Controller-owned base normalization to actual merged PR244 changes this identity and requires its own final review/evidence binding.

## Delivered behavior

AC-001: CohortEvidenceV1 constructor/parser and earned-autonomy schema admit minimum1; zero and bool are rejected. Empirical M7 producer currentness, blocked-bundle checks, recommendations, audits and zero-tolerance security behavior are unchanged. Existing thirty-row synthetic fixtures and dated v2.0.13 schedules remain historical/synthetic rather than factual acceptance records.

AC-002: new frozen typed OwnerPolicyV1, OwnerCaseV1 and OwnerActivationV1 with closed wire contracts. OwnerCaseV1 adapts the real completed Liqvera state: product source19284fb07fedd4909672c7e9a641cb066efbb7cc and factory sourcecb9af4073ba6c3d515145164d771c75ebdfa3224. Qualification requires accepted product and explicit owner-confirmed accounting/human readiness. OwnerRuntime implements actual activate/status/admit/revoke consumers. Initial L1 admits exactly local_read/local_test; ceilingL2 is not automatic promotion, and every decision denies external authority. CLI invokes that consumer each decision and does not execute an arbitrary command or provider action.

Activation binds policy/case digests, actual repository identity, clone/worktree Git-directory digest, actual HEAD/runtime source bytes, and the bounded local profile digest. Expiry is at most3600seconds and bounded by policy expiry2026-11-04. Missing, mismatched, disabled, expired, malformed, unsafe or revoked inputs return denied/L0. Descriptor-relative O_NOFOLLOW traversal pins runtime ancestors; final runtime directory is owned by the process user with mode0700. Immutable activation and policy-scoped revocation tombstone writes use O_EXCL and mode0600. Runtime lives only in ignored .grok-stack/runtime/owner-autonomy. Owner readiness is not an external signed security approval.

AC-003: PROJECT_STATE product version/current continuation, owner readiness and explicitly scoped m8_activation/m8_qualifying_cohort now reflect the bounded owner-local policy and one accepted product. Unknown cost_usd_micros and human_intervention_count remain null. Published2.1.1, prior releases, old pilot and milestone source receipts are retained; former cleanup continuation is preserved under historical_cleanup_continuation. Current README/START_HERE/roadmap name accepted-product PR244 and this2.2.0 successor, not an extra first pilot or thirty owner tasks. M9 source remains unchanged and explanation-only.

AC-004: VERSION and adaptive_grok.__version__ become2.2.0; README/CHANGELOG/package notes clearly identify source candidate versus latest published2.1.1. Architecture records additive executed paths and the new schema; existing rendered diagrams remain byte-identical. Release helper now references ignored dist ZIP/checksum directly, removing the copy into source packages, while exact-HEAD tag and no-main-push commands remain intact. Change spec maps all four criteria and has no UNKNOWN objective skeleton. No archive, tag, network/provider/production operation, push or merge was performed by writer.

## RED evidence

Command: PYTHONPATH=factory/src:. taskset -c 0-27 python3 -m unittest factory.tests.test_autonomy.OneAcceptanceFloorTests factory.tests.test_owner_autonomy

Observed: Ran2tests; FAILED(errors=2). Existing parser raised ContractError invalid_integer: minimum_human_acceptances at30 floor; new owner module import failed because the implementation was absent. These are expected missing-behavior controls, not a factual acceptance run. After implementation the same command passed9tests in0.331s.

Additional release-helper RED: PYTHONPATH=.grok-stack:. python3 -m unittest tests.test_deploy.DeployTests.test_human_commands_tag_exact_head_without_pushing_main

Observed: Ran1test in0.033s; FAILED(failures=1), assertion found a cp command. Minimal helper change removed cp/packages binary instructions and switched both release asset paths to dist.

## GREEN observations (focused, not qualifying receipts)

- PYTHONPATH=factory/src:. taskset -c 0-27 python3 -m unittest factory.tests.test_owner_autonomy factory.tests.test_autonomy factory.tests.test_autonomy_schema tests.test_project_state tests.test_structure — Ran85tests in4.089s, OK. Covers canonical blocked M7 and autonomy behavior, initial owner controls, and current state/version bindings.
- After removing the accidental test-only jsonschema dependency, PYTHONPATH=factory/src:. taskset -c 0-27 python3 -m unittest factory.tests.test_owner_autonomy — Ran11tests in1.442s, OK. Uses existing dependency-free SubsetValidator; no new dependency. Includes actual offline CLI lifecycle and source-currentness controls.
- PYTHONPATH=factory/src:.:.grok-stack taskset -c 0-27 python3 -m unittest tests.test_deploy tests.test_project_state.ProjectStateTests.test_current_owner_policy_is_bound_to_one_real_case_without_numeric_telemetry tests.test_manifest_package.PackageTests.test_published_zip_matches_immutable_release_record_and_embedded_manifest — Ran8tests in0.066s, OK. One earlier selector miss named nonexistent ManifestPackageTests and failed solely with AttributeError; corrected to PackageTests and passed.
- Post-commit HEAD-bound observation: PYTHONPATH=factory/src:.:.grok-stack python3 -m unittest tests.test_structure.StructureTests.test_repository_root_holds_only_canonical_entries tests.test_structure.StructureTests.test_version_identity_matches_readme — Ran2tests in0.008s, OK.
- python3 scripts/grok_spec.py validate --change-id 20261004-task-b25860 --gate --json — errors[], all4criterion IDs mapped. Initial colon/class suffix in test reference was rejected by path existence validation; corrected to real test module path. Later AC004 adds passing test_deploy reference.
- python3 scripts/grok_architecture.py validate --json and drift --json — findings[], oktrue. python3 scripts/grok_architecture.py diagram --check --json — mismatches[], oktrue. An initial nonexistent render subcommand was corrected to diagram. A worktree fitness observation was attempted but its completion output was not captured; it supplies no PASS claim and remains part of the controller's final gate.
- ruff check .grok-stack/adaptive_grok/deploy.py factory/src/adaptive_factory/owner_autonomy.py scripts/grok_m8.py factory/tests/test_owner_autonomy.py tests/test_deploy.py — All checks passed.
- bandit -q -c bandit.yaml factory/src/adaptive_factory/owner_autonomy.py scripts/grok_m8.py — no findings emitted.
- git diff --cached --check ran before commit, with no whitespace errors; clean git status after commit. Ignored private report/runtime paths confirmed by git check-ignore.

## Actual CLI consumer demonstration

test_cli_full_lifecycle_rechecks_actual_current_source_and_missing_inputs constructs a synthetic local Git checkout with the real CLI/module and factual state adapter, without network. subprocess CLI status→L0, activate→exit0, admit local_test→L1, admit provider_call→exit2; changing actual tracked module bytes makes admission return binding_mismatch; restoring bytes and revoke→exit0 makes subsequent admit return revoked/L0. Removing policy makes admission return exit2. This exercises persisted ignored runtime across separate processes; it does not claim deployed operational activation or synthetic telemetry for Liqvera. Controller performs real candidate/final-source activation after freeze.

## Scope/files

New: factory/src/adaptive_factory/owner_autonomy.py; factory/contracts/jsonschema/owner-autonomy.v1.schema.json; factory/runtime/owner-autonomy-policy.v1.json; factory/tests/test_owner_autonomy.py; scripts/grok_m8.py.

Modified runtime/contracts: factory/src/adaptive_factory/autonomy.py; factory/contracts/jsonschema/earned-autonomy.v1.schema.json; .grok-stack/adaptive_grok/__init__.py; .grok-stack/adaptive_grok/deploy.py; architecture/system.yaml.

Modified controls: factory/tests/test_autonomy.py; factory/tests/test_autonomy_schema.py; tests/test_project_state.py; tests/test_structure.py; tests/test_manifest_package.py; tests/test_deploy.py.

Modified state/docs: PROJECT_STATE.json; VERSION; README.md; START_HERE.md; DARK_FACTORY_ROADMAP.md; CHANGELOG.md; docs/package-status.md; decisions.md; mistakes.md.

Modified workflow package: engineering/changes/20261004-task-b25860/{change-spec.yaml,state.json,evidence/README.md,evidence/capacity.md}. Official grok_change transition entered implementing; AC001-004 mapped. No reviewer/subagent was spawned.

## Resource and verification omissions

Writer startup capacity was measured and privately recorded before route/source reads:14physical/28online logical, process22 CPUs/affinity0,1,8-27, effective inherited cpuset0-27, no finite actual-cgroup ancestor quota. Bounded child taskset probe confirmed28. One focused process ran at a time under allocated ceiling12; controller affinity was unchanged. Public writer summary is attached to capacity.md; complete private snapshot remains local.

Per explicit controller/user instructions, no full baseline, grok_verify, full discovery, coverage, PostgreSQL or Trust CI suite was run by writer. No completion receipt, external check or independent review is asserted. Controller must normalize actual PR244 base, persist selected independent code/test reviews, freeze and run the single whole-repository qualifying gate on the final report-containing source. This runtime/contract change requires full scope; historical component evidence grants no skip.

## Self-review, rollback and concerns

Self-review inspected actual new owner module/CLI and the staged diff: empirical route changes are limited to numerical floor; owner adapter never creates M4/M5/M6 rows; current handoff distinguishes source policy from deployed worker automation; release helper preserves exact-head/main-equality/tag instructions. Independent reviewers own approval and mutation evidence.

Rollback: run python3 scripts/grok_m8.py revoke in the affected clone; every later admission returnsL0. Disable the policy by ordinary reviewed source change if needed; normal reviewed revert restores previous source/version without rewriting published release identities. There is no schema migration or production deployment to roll back.

Concrete limitations: local L1 grants only named reads/tests; neither CLI nor generic worker gains local-edit/L2 promotion, arbitrary execution, provider, merge or production authority. L2 expansion requires a separate authorized policy/consumer change. Expired activation renewal requires removing only that clone's ignored activation.json then activating current source; revocation tombstone remains and requires new owner policy. Policy expiry is finite2026-11-04 and requires renewal decision after that date. Per-clone activation is intentionally absent from Git and controller-owned on the frozen/merged source. Full verification and independent review remain pending, and the unretrieved fitness attempt is not evidence.
