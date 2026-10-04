# Historical independent code review: REQUEST_CHANGES

Route6af9e6eed1d8; reviewed delta52e1163da49d80b1ee40210c48e565f2fa3f13e7..194cdc62fd6cd2bae1deeb93d60ad14d3738cf6b. Original PR base97a7581238022356b2de8d193a9bd8363fc92dc3. HEAD before/after194cdc62fd6cd2bae1deeb93d60ad14d3738cf6b; fingerprint before/afterb0a496e053b98766eb9992969bf09ace69064b0aa8c2d2fd99ed5eb567ec1182; candidate/restored scratch clean.

reviewed-tree-modified: no

Reviewer code_reviewer; private scratch relative to candidate ../adaptive-grok-build-pro/.review-scratch/receipt-code-EjOjoX/snapshot, under reviewer-owned non-sticky 0700 parents. Exact clean committed snapshot reproduced via local shared clone and restored.

P2 at receipts.py:765: classification serializes before guarded publication. A circular/unserializable value leaves prior verification=pass. Identical private reproducer at52e and194:

    GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:.grok-stack:tests taskset -c 0-3 python3 -B -c 'from test_verifier_recovery import routed_fixture,receipts
    with routed_fixture() as (root,route):
     receipts.write_receipt(root,"verification","pass")
     circular={}; circular["loop"]=circular
     try:
      receipts.write_receipt(root,"verification","pass",details=circular)
     except ValueError as error:
      print(type(error).__name__,str(error))
     old=receipts.get_receipt(root,route["route_id"],"verification")
     print("prior qualifying receipt retained:",old is not None and old.get("status")=="pass")'

Both raised ValueError Circular reference detected. Base52e retained=False;194 retained=True. Required repair: classification inside guarded publication; circular/nonserializable regressions; failure retires prior evidence. This is a failed historical review, not current gate evidence.

Positive batch command prefix:

    GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:.grok-stack:tests GROK_TEST_WORKERS=4 taskset -c 0-3 python3 -B -m unittest -v

Batch1 append targets:
    test_verifier_recovery.DurableReceiptRecoveryTests.test_large_scope_metadata_roundtrips_through_bounded_report
    test_verifier_recovery.DurableReceiptRecoveryTests.test_large_verification_report_preserves_complete_logs_and_scope
    test_verifier_recovery.DurableReceiptRecoveryTests.test_spilled_report_missing_tampered_and_unsafe_files_fail_closed
    test_verifier_recovery.DurableReceiptRecoveryTests.test_spilled_report_reference_and_all_envelope_bindings_are_closed
    test_verifier_recovery.DurableReceiptRecoveryTests.test_spilled_report_publication_faults_retire_prior_pass
    test_verifier_recovery.DurableReceiptRecoveryTests.test_report_publication_rechecks_source_before_receipt

Six passed13.673s. Batch2 append targets:
    test_verifier_recovery.DurableReceiptRecoveryTests.test_bounded_report_does_not_bypass_expected_tree_binding
    test_verifier_recovery.DurableReceiptRecoveryTests.test_oversized_report_still_fails_and_invalidates_prior_receipt
    test_verifier_recovery.DurableReceiptRecoveryTests.test_spilled_report_rejects_invalid_json_even_with_matching_hash
    test_verifier_recovery.DurableReceiptRecoveryTests.test_report_publication_rejects_symlink_directory_without_external_write
    test_verifier_recovery.DurableReceiptRecoveryTests.test_spilled_report_preserves_failed_cancelled_and_skipped_results
    test_verifier_recovery.DurableReceiptRecoveryTests.test_other_receipt_kinds_do_not_spill

Six passed22.497s. Complete1442checked/488rejected scope and logs retained; receipt cap262144, artifact cap8388608. Safe artifacts, immutable binding, explicit stale, publication faults, source recheck and status preservation exercised.

Private mutation commands used the same environment and `python3 -B -m unittest` followed by fully qualified targets:

- Bypass missing refusal/digest/size/binding: test_verifier_recovery.DurableReceiptRecoveryTests.test_spilled_report_missing_tampered_and_unsafe_files_fail_closed and test_verifier_recovery.DurableReceiptRecoveryTests.test_spilled_report_reference_and_all_envelope_bindings_are_closed. Killed13failures: missing/tampered, size, tenbindings.
- Reset stale hydration flag: test_verifier_recovery.DurableReceiptRecoveryTests.test_spilled_report_reference_and_all_envelope_bindings_are_closed. Killed1explicit-invalidation failure.
- Disable publication-failure cleanup: test_verifier_recovery.DurableReceiptRecoveryTests.test_spilled_report_publication_faults_retire_prior_pass. Killed6failures: write,replace,file/directoryfsync,cancellation.

All scratch mutations restored. No surviving/inconclusive mutants. Ruff receipts.py/test_verifier_recovery.py and GIT_OPTIONAL_LOCKS=0 git diff --check passed. Descriptor-relative report I/O and strict bindings inspected statically. Existing compact-envelope publication/directory preparation remain path based; not proof against every directory race. Full PR, PostgreSQL and external exact-head CI unexecuted; prior reports remain bound to original identities.
