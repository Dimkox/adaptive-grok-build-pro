# Historical independent test review: scoped PASS

Route6af9e6eed1d8; reviewed delta52e1163da49d80b1ee40210c48e565f2fa3f13e7..194cdc62fd6cd2bae1deeb93d60ad14d3738cf6b. Original PR base97a7581238022356b2de8d193a9bd8363fc92dc3. HEAD before/after194cdc62fd6cd2bae1deeb93d60ad14d3738cf6b; fingerprint before/afterb0a496e053b98766eb9992969bf09ace69064b0aa8c2d2fd99ed5eb567ec1182; candidate/restored scratch clean.

reviewed-tree-modified: no

Reviewer test_reviewer. Scratch ../adaptive-grok-build-pro/.review-scratch/test-review-spill-458o05/repo, reviewer-owned non-sticky0700 parents. Clone without hardlinks reproduced HEAD/fingerprint; restored scratch matched. Capacity2026-10-04T14:26:43Z:14physical/28online, defaultaffinity22, effectivecpuset0-27, unlimitedancestorquota, successfulchildprobe; allocation4CPUs.

Inspected actual implementation, tests and architecture note. Only large verification details spill, cap262144unchanged, finite reportcap8388608; exact bytes/hash/immutable binding, stale preservation and failure retirement exercised. Later independent code review found classification-serialization P2 not covered by these probes; this scoped PASS is historical, not complete gate evidence.

From scratch repo, GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.grok-stack:tests TMPDIR=private sibling tmp; command `taskset -c 0-3 python3 -m unittest -v` with these exact targets:
    test_verifier_recovery.DurableReceiptRecoveryTests.test_large_scope_metadata_roundtrips_through_bounded_report
    test_verifier_recovery.DurableReceiptRecoveryTests.test_large_verification_report_preserves_complete_logs_and_scope
    test_verifier_recovery.DurableReceiptRecoveryTests.test_bounded_report_does_not_bypass_expected_tree_binding
    test_verifier_recovery.DurableReceiptRecoveryTests.test_oversized_report_still_fails_and_invalidates_prior_receipt
    test_verifier_recovery.DurableReceiptRecoveryTests.test_spilled_report_missing_tampered_and_unsafe_files_fail_closed
    test_verifier_recovery.DurableReceiptRecoveryTests.test_spilled_report_reference_and_all_envelope_bindings_are_closed
    test_verifier_recovery.DurableReceiptRecoveryTests.test_spilled_report_rejects_invalid_json_even_with_matching_hash
    test_verifier_recovery.DurableReceiptRecoveryTests.test_spilled_report_publication_faults_retire_prior_pass
    test_verifier_recovery.DurableReceiptRecoveryTests.test_report_publication_rechecks_source_before_receipt
    test_verifier_recovery.DurableReceiptRecoveryTests.test_spilled_report_preserves_failed_cancelled_and_skipped_results
    test_verifier_recovery.DurableReceiptRecoveryTests.test_other_receipt_kinds_do_not_spill

11passed22.803s. Complete1442/488 and logs roundtrip; expectedtree; missing/tamper/symlink/FIFO/oversize; malformedJSONmatchinghash; closed reference and10envelope fields; explicit stale; write/rename/fsync/cancel; source change; failed/cancelled/skipped; other-kinds no-spill.

Mutation commands use the same environment and `taskset -c 0 python3 -m unittest -v` followed by the exact target:

- Remove digest check: test_verifier_recovery.DurableReceiptRecoveryTests.test_spilled_report_missing_tampered_and_unsafe_files_fail_closed. Killed exit1 same-lengthtamper accepted;4.037s.
- Remove envelopebinding: test_verifier_recovery.DurableReceiptRecoveryTests.test_spilled_report_reference_and_all_envelope_bindings_are_closed. Killed exit1 tenfields accepted;0.909s.
- Drop stale: same target. Killed exit1 KeyError stale;0.990s.
- Remove publicationcap: test_verifier_recovery.DurableReceiptRecoveryTests.test_oversized_report_still_fails_and_invalidates_prior_receipt. Killed exit1 reportremainedpass;1.583s.

No surviving/inconclusive mutants. Publication overflow used reducedtestcap; read overflow actual8MiB. Exact publicationboundary and concurrentmutation duringread were not separately probed. Full verifier/unrelateddiscovery/PostgreSQL/externalCI unexecuted; earlierreviews historical. Current fresh verification remains necessary.
