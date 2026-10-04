# Historical code review: request changes

This is superseded component evidence, not final approval. Reviewer: independent `code_reviewer`. Source HEAD: `7da46ca2d4ab2e30e7e2a2a19ee4cf53915095b6`; candidate fingerprint before and after: `206e385fab16d6e8b5f27ce39acedf3b36e2be3e9e85d8e2993846f7e785828c`.

Scratch: `../adaptive-grok-build-pro/.review-scratch/cleanup-code-BQ2zAM/snapshot`, under a trusted non-sticky private 0700 parent. Exact clean candidate copied; mutations occurred only in scratch, then were restored. reviewed-tree-modified: no

## Findings

1. QG-01 accepted `python-focused-unittest` without an eligible docs/state scope or disclosed replaced discovery/coverage records.
2. QG-01 accepted `pytest` without any coverage record.

Both exact reproductions returned `pass`, despite removing `python-unittest` and `coverage` from `BASE_PR_CHECKS` and adding only the named replacement runner. Command: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.grok-stack:tests taskset -c 0-3 python3 -B -c 'from adaptive_grok.quality_gates import evaluate_quality_gate; from test_quality_gates import BASE_PR_CHECKS,check; checks=[item for item in BASE_PR_CHECKS if item.name not in {"python-unittest","coverage"}]; print("focused-without-eligible-scope", evaluate_quality_gate(mode="pr",checks=[*checks,check("python-focused-unittest")]).status); print("pytest-without-coverage",evaluate_quality_gate(mode="pr",checks=[*checks,check("pytest")]).status)'`.

## Executed claims

Prefix for unittest commands: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.grok-stack:tests GROK_TEST_WORKERS=4 taskset -c 0-3 python3 -B -m unittest -v`.

Arguments: `test_quality_gates test_verification_doctor.TypedSpecVerificationTests.test_proven_v1_retirement_is_disclosed_without_current_gate_evidence test_verification_doctor.TypedSpecVerificationTests.test_retirement_rejects_tampered_missing_active_current_and_unknown_specs test_verification_doctor.TypedSpecVerificationTests.test_v2_cannot_be_archived_and_relocation_keeps_strict_gate test_architecture_fitness.ArchitectureFitnessTests.test_exact_batch_blob_reader_is_bounded_and_validates_entries`. Result: 8 tests passed in 2.895 s.

Arguments: `test_installer.InstallerTests.test_payload_is_sorted_safe_duplicate_free_and_profile_explicit test_installer.InstallerTests.test_installed_template_artifacts_are_explicit_reusable_source test_change_spec.ChangeSpecTests.test_canonical_json_parser_rejects_ambiguous_or_unbounded_input`. Result: 3 tests passed in 1.686 s.

## Mutation probes

- Disable archive checksum guard: the existing invalid-YAML tamper test survived because YAML parsing independently rejected its input. This was a test limitation, not approval. The reviewer then appended a valid YAML comment without updating the digest in a private probe. Baseline rejected it; the mutant admitted it and failed the assertion: killed by `PYTHONPATH=.:.grok-stack:tests python3 -B ../probe_archive_checksum.py`.
- Disable schema-version matching and active-package archive guard: the retirement rejection and v2 relocation tests failed for the corresponding cases; killed.
- Disable missing-coverage finding: `test_quality_gates.QualityGateTests.test_pr_fails_when_mandatory_check_is_missing` failed; killed.

No full suite, PostgreSQL exit suite, external Trust CI or broad documentation audit was executed by this reviewer. Architecture fitness was independently known to fail. This report does not establish merge eligibility.
