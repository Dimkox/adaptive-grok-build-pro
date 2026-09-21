# Architect analysis — issue #162

## Verified boundary

`receipts.RECEIPT_KINDS` and `workflow_artifacts.RECEIPT_KINDS` each contain seven kinds; `schemas/change-spec.schema.json` v2 permits only five in `$defs.evidence.properties.receipt.enum`. `spec.validate_spec()` applies that enum and `verification._change_specs()` calls it at the PR gate. Thus a routed `bitrix_review` or `data_review` receipt cannot be cited in a valid typed spec. The schema is a vocabulary constraint, not an authority to create or accept receipts.

## Smallest coherent design

Add `bitrix_review` and `data_review` to the v2 schema enum. Add a test asserting set equality between the schema enum and both runtime sets, plus validation tests showing the two restored kinds pass and an unknown kind fails. Keep receipt issuance, route evidence requirements, and gate semantics untouched. This is additive within the existing v2 contract; no version bump or migration is needed.

The issue's proposed earlier scaffold validation is a separate improvement. `change.start_change()` generates a draft spec, while gate validation checks completion and references that do not yet exist. Running gate validation at scaffold time would reject legitimate drafts. A schema-only check after generation could improve diagnostics, but is not needed to close this mismatch and should not broaden this fix.

## Regression and recovery

Guard against comparing only subset membership: exact equality catches future missing and unrecognized enum values. Verify acceptance through `spec.validate_spec(..., schema_only=True)` or equivalent schema validation, and reject a made-up receipt. Rollback is reverting the additive enum and tests before merge; after use, a forward fix is safer because reverting would invalidate specs already citing the two legitimate kinds. No external state changes.
