Persisted Stage A evidence only: source HEAD `39d0f9eb27d807e72219d613c290e785a035f151`, fingerprint `b7c59b62ec6e3d29e4d09376f74bc22975bf5198767a74991570e0484b52d68c`. The complete report below is projected only by replacing the host repository prefix with `<repository-root>` and removing trailing whitespace. Actual 004 pin, final reviews and final verification remain pending; this is historical source-bound evidence, not a completion receipt.

# Draft checker implementation handoff

Status: draft implementation committed; not independently reviewed or locally qualified for delivery. Production reviewed-migration registry is EMPTY. Actual Task1 004 bytes and independent SQL review do not yet exist in this contour. No migration pin, external operation, approval or merge claim is made.

## Exact source identity

Repository: <repository-root>/.review-scratch/trust-public-checker
Branch: fix/trust-public-local-checker
Route: 249e86df9131; change: 20261005-task-249e86
Agreed actual base: 326908bf6367b05b65b83818ee84a093c1e45872
Starting HEAD: fd5f5fcc32358bb07c51c23881bede751e76f197
Draft HEAD: 39d0f9eb27d807e72219d613c290e785a035f151
Draft Git tree: f0fb961fd7f3a3469cc6253ace8bb508065ecd4c
Product checker SHA256: a7705e636074781464b5fb5830e0de03dd7bf007b00cbf45a403162890f09be5
Focused tests SHA256: 3d53af0d00acd1dd97d22e3c97b310d37eb3bc824065d56ec98400e90f267c6c
Commit changes only .grok-stack/adaptive_grok/architecture_fitness.py, tests/test_architecture_fitness.py and the three-sentence decisions.md memory entry: 390 insertions / 5 deletions. Base..HEAD additionally includes the already committed 14-file controller scope/evidence package, totaling 17 files / 1006 insertions / 5 deletions. Git status after commit was clean.

Ignored report parent .review-scratch and implementer-owned scratch .review-scratch/checker-private-GVgoL3 are owned by pall, mode 0700. This is an implementer report, not an independent reviewer report; no mutation-score or self-approval is claimed. Capacity recheck is recorded in .review-scratch/checker-capacity.md.

## Change and bounds

The reviewed-byte exception counts exactly trust-ci/sql/004_public_admission.sql as version 4, but accepts its bytes only when the private checked-in raw-SHA256 registry contains that exact path/hash, the existing exact Trust CI migration policy remains intact, and the sole exact packaged mirror is byte-identical. The registry is empty. History immutability, numeric contiguity, uniqueness, aggregate work/byte/statement limits and the generic phase analyzer remain. Unknown SQL inventory now fails closed rather than disappearing from migration version analysis. Named successful reviewed-byte compatibility explicitly says "not semantic phase proof" and includes the raw digest; no arbitrary numbered migration fallback or caller digest parameter was introduced.

Four exact version-1 descriptors may be removed from a comparison copy only with their precise kind/role/compatibility and sole prescribed owner. A changed schema and nonempty changed source bytes are required. Lifecycle pairs only api.py or webhooks.py under the existing API owner; selection/effective policy pair only public_policy.py; public attestation pairs only public_runner.py. Unrelated policy.py edits cannot qualify these descriptors. Removal recovers the existing envelope comparison, including every old contract/node attribute and all edges/domains.

Worker source additions are only the seven named files on the existing NODE-TRUST-CI-WORKER, preserving execution domain, owner, type, runtime, secrets and all prior memberships. Global worker type/domain permissions were not widened. Existing API/OpenAPI/store.py correction controls still pass. No generated-diagram exception was added. Factory/checker/rule/schema implementation mixed with Trust CI still fails.

## RED evidence

Exact command:
```
taskset -c 4-7 python3 -m unittest tests.test_architecture_fitness.ArchitectureFitnessTests.test_change_separation_admits_only_exact_paired_public_contracts tests.test_architecture_fitness.ArchitectureFitnessTests.test_public_worker_source_membership_is_exact_and_envelope_preserving
```
Exit 1; 2 tests / 12 expected failures in 31.629 s: four individual public contracts plus their combined addition, and all seven allowed worker filenames returned fail rather than pass. The unrelated extra worker filename stayed denied. An initial fixture-only run mistakenly called _json_schema without its required argument; that setup was corrected before the observed RED above and is not counted as regression evidence.

Exact command:
```
taskset -c 4-7 python3 -m unittest tests.test_architecture_fitness.ArchitectureFitnessTests.test_reviewed_public_migration_uses_named_byte_compatibility_not_phase_proof
```
Exit 1; 1 expected failure in 2.083 s: synthetic reviewed exact 004 returned unsupported, finding "migration phase cannot be derived", rather than named byte compatibility.

## GREEN evidence

Final affected command, after adding all currently executed node/prefix cases:
```
taskset -c 4-7 python3 -m unittest tests.test_architecture_fitness.ArchitectureFitnessTests.test_change_separation_public_contracts_preserve_original_envelope tests.test_architecture_fitness.ArchitectureFitnessTests.test_change_separation_admits_only_exact_paired_public_contracts tests.test_architecture_fitness.ArchitectureFitnessTests.test_public_worker_source_membership_is_exact_and_envelope_preserving tests.test_architecture_fitness.ArchitectureFitnessTests.test_reviewed_public_migration_uses_named_byte_compatibility_not_phase_proof tests.test_architecture_fitness.ArchitectureFitnessTests.test_reviewed_public_migration_refuses_drift_and_incomplete_history tests.test_architecture_fitness.ArchitectureFitnessTests.test_unreviewed_public_migration_cannot_accept_runtime_digest_authority tests.test_architecture_fitness.ArchitectureFitnessTests.test_change_separation_metadata_does_not_hide_implementation
```
Exit 0; Ran 7 tests in 138.155 s; OK. Every subTest case in the matrix below actually executed.

Exact additional command:
```
taskset -c 4-7 python3 -m unittest tests.test_architecture_fitness.ArchitectureFitnessTests.test_public_metadata_requires_changed_schema_and_exact_paired_source_bytes tests.test_architecture_fitness.ArchitectureFitnessTests.test_public_lifecycle_metadata_accepts_existing_api_owned_webhook_pair
```
Exit 0; Ran 2 tests in 6.580 s; OK. The unchanged-source setup first contained no changed Trust CI path, so the separation rule correctly passed without qualifying any metadata; the test was corrected to include an unrelated legacy policy.py edit and now exercises refusal of that attempted pairing.

Exact preserved-control command:
```
taskset -c 4-7 python3 -m unittest tests.test_architecture_fitness.ArchitectureFitnessTests.test_migration_history_and_required_phases_fail_closed tests.test_architecture_fitness.ArchitectureFitnessTests.test_canonical_migrations_seed_phased_version_history tests.test_architecture_fitness.ArchitectureFitnessTests.test_migration_history_requires_declared_resource_mirror tests.test_architecture_fitness.ArchitectureFitnessTests.test_migration_mirror_only_change_is_applicable_and_fails_drift tests.test_architecture_fitness.ArchitectureFitnessTests.test_migration_planning_and_blob_comparison_are_aggregate_bounded tests.test_architecture_fitness.ArchitectureFitnessTests.test_migration_work_and_published_findings_have_explicit_limits tests.test_architecture_fitness.ArchitectureFitnessTests.test_migration_shared_root_memberships_are_charged_before_matching tests.test_architecture_fitness.ArchitectureFitnessTests.test_migration_empty_selector_amplification_is_bounded_after_validation_bypass tests.test_architecture_fitness.ArchitectureFitnessTests.test_migration_blob_statement_and_finding_limits_stop_early tests.test_architecture_fitness.ArchitectureFitnessTests.test_migration_content_and_versions_are_conservative_for_every_status tests.test_architecture_fitness.ArchitectureFitnessTests.test_migration_phase_identity_rejects_duplicate_artifacts tests.test_architecture_fitness.ArchitectureFitnessTests.test_change_separation_rejects_product_and_trust_ci_mixing tests.test_architecture_fitness.ArchitectureFitnessTests.test_change_separation_admits_bound_trust_ci_metadata
```
Exit 0; Ran 13 tests in 20.419 s; OK.

Earlier positive GREEN: the RED pair plus reviewed-byte positive ran 3 tests in 31.835 s, OK. Earlier negatives before the two added node/prefix cases ran 4 tests in 118.616 s, OK. These are earlier observations of this draft development sequence, not reused qualification receipts.

Exact candidate diagnostic command:
```
taskset -c 4-7 python3 scripts/grok_architecture.py fitness --base 326908bf6367b05b65b83818ee84a093c1e45872 --worktree --json
```
Exit 0; fitness_status=pass, exact_base_sha=326908bf6367b05b65b83818ee84a093c1e45872, architecture changes=[], change_separation/code_budget/module_boundary=pass, migration_safety=not_applicable because this checker-only candidate has no changed SQL. Same product bytes as the committed draft; this ran before adding the decisions.md prose entry. Architecture evidence digest 303b0a3b9d63a32399de11bba15b6c3fc6bf0b0840a1e3f02080e7d8f6272acd. It is diagnostic evidence, not a full verification receipt.

git diff --check exited 0 before commit. git status --short after commit had no output. No preliminary full-suite or grok_verify receipt was run.

## Actually executed closed cases

Public positives: each of the four contracts alone; all four together; api.py and webhooks.py lifecycle pairs; all seven exact worker files public_models.py, public_admission.py, public_policy.py, source_safety.py, public_storage.py, public_checkout.py, public_runner.py. public_extra.py remained denied.

Public envelope negatives (26): path, identity, version, kind, role, compatibility, contract_owner, missing_source, unrelated_source, missing_registration, worker_runtime, worker_secrets, worker_owner, worker_domain, worker_type, old_binding, old_contract, edge, node, new_node, worker_prefix, arbitrary_source, extra_schema, local, checker, rules. Added unchanged-schema and unchanged-exact-source negatives both execute with an unrelated changed legacy Trust CI source to make the separation boundary applicable.

Existing metadata negatives (12, replacing the old three-entry loop): runtime, secret, edge, owner, other_source, wildcard, local, checker, rules, schema, contract, contract_role. These previously present branch labels now actually execute.

SQL negatives (13): paired_drift, mirror_drift, missing_mirror, mirror_only, primary_deleted, history_modified, history_deleted, history_gap, duplicate_version, other_005, unknown_sql, wrong_primary_path, wrong_mirror_path. Existing named conservative/status/limit/phase tests retained and executed. Production synthetic-byte refusal executes despite candidate SHA256 supplied in two environment variables; caller expected_digest raises TypeError; --expected-migration-digest is rejected by the real CLI as unrecognized arguments. The positive reviewed registry is patched only privately inside the explicit synthetic fixture test; no production hash is derived or pinned from candidate input.

## Self-review, limitations and next handoff

Read actual checker diff and surrounding source, migration policy and actual existing worker/API registrations. Removed duplicate qualified architecture path output by deduplicating the evidence tuple. The diagnostic candidate fitness check confirms unchanged product architecture and no Trust CI implementation mixing. These checks are implementer observations only.

Unexecuted claims: actual 004 PostgreSQL syntax/function bodies, additivity/destructiveness, roles/grants, quotas, concurrency/admission linearization, locks, query plans, bounded cleanup, recovery, real migration apply/status compatibility, production deployment, holdout/App CI and signed approvals. No PostgreSQL/container/runtime operations were attempted, and no actual migration is present here. Raw byte identity cannot establish those semantics. Independent selected code/test/security/data/release review and reviewer private mutation probes remain controller work; no review receipt is recorded by the implementer.

The controller must obtain frozen actual Task1 bytes with source identity and independent review, then send the actual reviewed raw SHA256 back to this sole writer. Any actual pin is a subsequent source change needing affected controls and fresh review identity. Keep the production registry denying until that handoff. After complete independent reports are persisted and committed, the controller owns the one final full PR verifier and exact-head external Trust CI path. Rollback is a separate protected revert/fix PR; no deployed state/history rewrite is authorized.

Implementer stops at this committed draft.
