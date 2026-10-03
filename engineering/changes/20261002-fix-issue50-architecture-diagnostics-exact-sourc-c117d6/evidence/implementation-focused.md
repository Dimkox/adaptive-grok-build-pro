# D implementation and focused evidence

Route c117d6185b7f; selected sole writer general_implementer; isolated branch fix/v211-architecture-preflight. Source starting HEAD e5856acfd4bc7a186f40a740b54ec86459462db5. Implementation commit 59f0a9cd3e06b5a3c8599f260aa221b7a836daf3; actual main 63799f8760d3a55028d83ab5ff0116ececf8f7d1 merged cleanly at ab24e1fbabbcadb893522edf946a0f01a1fa277f. The merge retained the implementation's source bytes; a final cross-input alias regression then required a small shared-identity-map loader correction. The approved recovery design section D and four independent analysis reports supply scope, not new verification evidence. Old arch50 was read-only input and none of its evidence commits were copied.

Implemented additive ArchitectureError document/line/column coordinates, raw document/path-shape refusal, duplicate normalized declared paths, descriptor-bound input aliases, actual syntax/duplicate-key positions and bounded actual model/schema/referenced-contract loading. Physical LF counting preserves Unicode lookalike semantics. Doctor discloses absent inputs as info/skipped and actual refusal as fail. The verifier's separately named architecture-inputs gate runs before binding/fitness, retains aggregate failure diagnostics and discloses dependent checks not started. Refused inputs return a failed report with receipt_status=not_recorded and receipt-not-recorded details rather than trying to rebind a receipt.

Repository ownership anchors remain source inventory checked downstream; they are not additional documents loaded by the model. Existing adoption/history authority, digests, generated views, A's runner/finalization tail, E's Git helpers and main's factory subset-contract preflight remain intact.

Executed RED: taskset-constrained new 14-test module on original source produced 35 failures and one missing-doctor-item error; the root-discovery marker really ran after malformed input. Additional REDs proved refusal receipt rebinding raised, missing disclosure metadata raised KeyError, and nested same-key duplicate coordinates selected line 3 rather than literal expected 6. These failures have focused regressions. Intermediate compatibility failure from treating ownership inventory as load inputs was corrected and recorded in mistakes.md.

Executed focused GREEN:

- taskset -c 8 python3 -m unittest tests.test_architecture_model_preflight tests.test_architecture_model tests.test_architecture_fitness -q: 229 tests, 69.112 seconds, OK, exit 0 before the final cross-input alias hunk.
- Final changed-source run of that same command: 230 tests, 112.597 seconds, OK, exit 0, after the complete-input identity-map repair and its seventeenth preflight regression.
- taskset -c 9 python3 -m unittest tests.test_verification_doctor -q: 86 tests, 196.025 seconds, OK, exit 0. A post-main rerun passed all 86 tests in 241.783 seconds after the receipt-disclosure and duplicate-coordinate corrections, before the final cross-input alias hunk. These are nearby compatibility evidence, not final-tree receipts.
- Final changed-source verifier cases: taskset -c 9 python3 -m unittest tests.test_verification_doctor.VerificationTests.test_verify_reports_architecture_metadata_without_exact_worktree_sha tests.test_verification_doctor.VerificationTests.test_governance_runs_after_spec_and_architecture_and_failure_is_not_receipted tests.test_verification_doctor.VerificationTests.test_adoption_marker_read_fails_when_nofollow_is_unavailable tests.test_verification_doctor.VerificationTests.test_missing_adoption_marker_cannot_disable_architecture_checks tests.test_verification_doctor.VerificationTests.test_verify_fails_after_committed_deletion_of_both_adopted_models -q: 5 tests, 88.761 seconds, OK, exit 0.
- Scoped ruff check on architecture.py, doctor.py, verification.py and test_architecture_model_preflight.py: all checks passed, exit 0.
- git diff --check: exit 0.
- load_spec/validate_spec: ok=true, concrete typed criteria accepted.

Product source SHA256 values after the final cross-input alias hunk:

| Path | SHA256 |
| --- | --- |
| .grok-stack/adaptive_grok/architecture.py | 57869427377a204e5f00243303a053bac08d36eddce51a498b7e77232880e19a |
| .grok-stack/adaptive_grok/doctor.py | 5644962aa9f3fe6a5478cabec8d3f8ecb02467d7904e2999147bd611b20be9f8 |
| .grok-stack/adaptive_grok/verification.py | caf4b08d03fc2a1da70bb96763aa9c0b6afd43d43603cfe2ebc239c1703fd52d |
| tests/test_architecture_model_preflight.py | b698577554c7fbb1837e702db3ce2a44defbe4d46afb21095ec2c20a83e8816f |

Both focused contours use the controller-verified child affinity, CPUs 8 and 9, at most two test processes total. This is focused implementation evidence only: full current PR verification, selected independent reviews, final fingerprint receipts and external exact-head Trust CI remain controller obligations. No push, merge to a protected/shared branch, publication, deployment or approval action was taken by this writer.

Aggregate integration boundary: A has moved the verifier body into _verification_run and owns the wrapper/report/runner finalization. Insert D's preflight inside that body and preserve the exact input-refusal receipt-not-recorded state alongside A's evidence_status=not_recorded; never replace A's tail with this predecessor's tail. E retains ownership of architecture_diff Git helpers.
