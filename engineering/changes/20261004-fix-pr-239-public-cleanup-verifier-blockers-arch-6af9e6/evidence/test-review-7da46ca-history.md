# Historical test review: bounded pass

Superseded component evidence, not final approval. Reviewer: independent `test_reviewer`. Source HEAD: `7da46ca2d4ab2e30e7e2a2a19ee4cf53915095b6`; candidate fingerprint before and after: `206e385fab16d6e8b5f27ce39acedf3b36e2be3e9e85d8e2993846f7e785828c`.

Scratch: `../adaptive-grok-build-pro/.review-scratch/test-review-pbSKzi/repo`; trusted non-sticky private 0700 parent. Exact clean snapshot; mutations were made only in scratch and restored. reviewed-tree-modified: no

All commands used `PYTHONDONTWRITEBYTECODE=1`, private scratch `TMPDIR`, and `PYTHONPATH=.grok-stack:tests:factory/src:factory/tests`.

## Executed claims

`taskset -c 0-3 python3 -m unittest -v test_architecture_fitness.ArchitectureFitnessTests.test_analysis_memory_constants_are_pinned test_architecture_fitness.ArchitectureFitnessTests.test_aggregate_artifact_budget_counts_deleted_binary_bytes test_installer.InstallerTests.test_target_without_record_delivers_every_source_managed_path_intact test_factory_v15_bundle.FactoryV15BundleTests test_verification_doctor.TypedSpecVerificationTests.test_proven_v1_retirement_is_disclosed_without_current_gate_evidence test_verification_doctor.TypedSpecVerificationTests.test_retirement_rejects_tampered_missing_active_current_and_unknown_specs test_verification_doctor.TypedSpecVerificationTests.test_v2_cannot_be_archived_and_relocation_keeps_strict_gate test_quality_gates.QualityGateTests`: 11 tests passed in 2.027 s.

`taskset -c 0-3 python3 -m unittest -v test_change_receipts.ChangeTests.test_public_change_slug_is_neutral_for_every_title test_change_receipts.ChangeTests.test_change_path_does_not_depend_on_title_and_start_is_idempotent test_hooks.HookTests.test_root_shim_dispatches_pre_tool_use test_hooks.HookTests.test_root_shim_fail_open_when_canonical_missing test_landing_api.LandingApiTests.test_predecessor_contract_migration_showcase_and_published_release_record_are_frozen`: 5 tests passed in 0.435 s.

## Mutation probes

- Exclude base bytes when a binary is deleted: `taskset -c 0 python3 -m unittest -v test_architecture_fitness.ArchitectureFitnessTests.test_aggregate_artifact_budget_counts_deleted_binary_bytes` exited 1 (`ArchitectureError` not raised); killed.
- Disable root-hook template substitution: `taskset -c 1 python3 -m unittest -v test_installer.InstallerTests.test_target_without_record_delivers_every_source_managed_path_intact` exited 1 (`UnsafeInstallTarget`, missing `post_tool_use`); killed.
- Tamper the first hexadecimal character of the public document projection checksum: `taskset -c 2 python3 -m unittest -v test_factory_v15_bundle.FactoryV15BundleTests` exited 1 (pinned hash mismatch); killed.

The other eight hook dispatch paths, rejection of extra redaction metadata fields, full coverage, PostgreSQL exit and external Trust CI were not executed. Old ZIP validation now establishes only the retained immutable published record, not fresh ZIP-byte validation. Architecture fitness blocked overall delivery independently.
