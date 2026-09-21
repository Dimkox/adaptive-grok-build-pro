# Repo exploration — issue #162

## Reproduction and root cause

On this worktree, a read-only comparison of `.grok-stack/adaptive_grok/receipts.py::RECEIPT_KINDS` with `schemas/change-spec.schema.json::$defs.evidence.properties.receipt.enum` returns seven runtime kinds and five schema kinds; `bitrix_review` and `data_review` are missing from the schema. The router emits both from selected domain reviewers (`.grok-stack/adaptive_grok/router.py:410-415`), and `scripts/grok_review.py:15` accepts both. `spec.validate_schema` rejects any receipt outside the enum (`.grok-stack/adaptive_grok/spec.py:338-341`), so a typed change spec citing either required review fails validation. The first incorrect state is the independently maintained schema enum, not receipt creation or route selection.

The existing parity test in `tests/test_workflow_artifacts.py:793-820` covers router emission, `workflow_artifacts.RECEIPT_KINDS`, and `receipts.RECEIPT_KINDS`, but does not inspect the schema. `verification._change_specs` calls `validate_spec` for selected specs at the PR/release gate (`.grok-stack/adaptive_grok/verification.py:752-790`).

## Smallest repair and regression surface

- Add the two missing enum members to `schemas/change-spec.schema.json:17`; preserve the seven-kind closed enum and rejection of unknown values.
- Extend `tests/test_change_spec.py` to assert exact set parity with the runtime receipt kinds, successful `SPEC.validate_spec` for each known receipt in an otherwise valid spec, and rejection of an unknown receipt. This tests the actual spec validator instead of only comparing lists. Existing `VALID_SPEC` and `ChangeSpecTests` at lines 29-86 provide a compact fixture.
- `scripts/grok_change.py` currently has only `start`, `transition`, and `show` (`:15-33`); `generate_spec` creates an empty scaffold (`spec.py:805-829`). Validating that empty scaffold earlier would not catch a later author-supplied receipt. The issue's suggested early scaffold check is therefore separate behavior, not needed for this parity repair.

This is additive contract compatibility for two already emitted runtime values. It does not change receipt authority, route-required evidence, or gate semantics. No product files or tests were changed during this analysis.
