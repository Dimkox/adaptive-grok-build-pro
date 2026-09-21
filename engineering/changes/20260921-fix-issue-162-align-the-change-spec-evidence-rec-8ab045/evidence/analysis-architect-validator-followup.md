# Architect follow-up — shipped validators for issue #162

## Finding

The schema repair alone leaves a reproducible shipped-source inconsistency. `trust-ci/src/adaptive_trust_ci/runner.py:_RECEIPT_KINDS` and `trust-ci/holdout.example/change_spec_validate.py:RECEIPT_KINDS` each still contain only five kinds. Runner `_metadata_evidence()` rejects `bitrix_review`/`data_review` while `extract_spec_metadata()` processes a changed spec, before holdout commands; a failure becomes signed `typed-spec-metadata` evidence. The independent example holdout's `_evidence()` rejects the same values in `_validate_document()`. Both are vocabulary checks on spec references, not proof that a receipt was actually issued. Unknown kinds must remain rejected.

## Minimal source-only completion

Add the two missing names to both checked-in validator sets, retaining every other validation rule. Add a focused `trust-ci/tests/test_runner.py` case that runs `extract_spec_metadata()` on each newly valid receipt and an unknown receipt, asserting valid coverage/digest for the former and `SpecMetadataError` for the latter. Add analogous `trust-ci/tests/test_change_spec_holdout.py` cases through `_validate_document()` using its complete valid fixture. A parity test should compare both validator sets against the schema/runtime receipt vocabulary so another divergence fails locally. No new receipt issuer, approval scope, check name, or bypass is introduced; accepting these two names only permits citing already supported route-required evidence.

## Trust boundary

These files are repository source. The deployed Trust CI worker image and server-mounted holdout are outside the pull-request trust domain. Updating `holdout.example` does **not** update the deployed holdout; updating runner source does **not** update the running worker. A current external check may still reject such a spec until the separately reviewed and authorized runner/holdout rollout and policy-epoch check are completed. Do not alter deployed policy, holdout bundle, keys, services, or branch protection in this issue. Local tests establish source consistency only; exact-PR-head external Trust CI remains merge authority.
