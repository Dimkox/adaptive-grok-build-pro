# Validation plan and measured status

Executed here: only path-scoped three-way Git application and static diff/conflict inspection. `git diff --cached --check` passed before source commit. No tests, lint, compilation, Docker, import probes or full gate ran. Historical September19 checks belong to stale heads and are not this candidate's evidence.

Parent-controlled focused command after the candidate is frozen:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tests:.grok-stack python3 -m unittest test_human_gates test_change_spec test_structure.StructureTests.test_reviewer_mutation_probes_are_scratch_only_and_reported test_verification_doctor.TypedSpecVerificationTests test_verification_doctor.VerificationTests.test_diff_check_keeps_non_utf8_filename_failure_serializable test_verification_doctor.VerificationTests.test_run_decode_opt_in_preserves_strict_default_and_timeout_contract test_package_status test_change_receipts.ChangeTests
```

Required integration cases before readiness:

1. Gated transition refusal does not alter checkpoint/history; successful first implementation preserves the original checkpoint.
2. Fresh empty and populated status remain nonmutating. A selected `state.json` or `route.json` symlink, FIFO, oversized/unreadable file must not be reopened by the new gate status path after package inspection refuses it.
3. Existing active packages without newly persisted gate fields have a deliberate upgrade path; never silently discard a declared gate or manufacture approval. The incoming implementation currently reports a missing/malformed/changed declaration for those packages, so compatibility requires an explicit decision and test.
4. Preserve all-category coverage while existing v1 signed AC projections remain unchanged.
5. Preserve non-UTF-8 filenames, subprocess timeout/127 contracts and default strict decoding through later actually delivered lifecycle integration.

The coordinator owns the one serialized full PR gate, independent code/test/security/release reviews and final fingerprint-bound receipts. User batch/no-op instructions prevail over generic repeated-gate wording in retained workflow documents.
