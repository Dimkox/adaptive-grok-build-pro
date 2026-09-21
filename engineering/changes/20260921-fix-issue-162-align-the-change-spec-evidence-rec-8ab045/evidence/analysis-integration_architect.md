# Integration architect analysis — issue #162

## Producer and consumer boundary

`router.py` derives `required_evidence` from selected reviewers, including `bitrix_review` and `data_review` (around lines 404–422). Both runtime registries, `receipts.py::RECEIPT_KINDS` and `workflow_artifacts.py::RECEIPT_KINDS`, contain seven kinds. The typed change-spec consumer has a separate enum in `schemas/change-spec.schema.json::$defs.evidence.properties.receipt`, containing only five. `spec.validate_spec()` loads that schema; `verification._change_specs()` calls it for the active spec. Thus a route can mandate evidence that its spec cannot name. The two runtime sets already have a parity test in `tests/test_workflow_artifacts.py`; the schema is outside that assertion.

## Bounded recommendation

Add the two missing enum values and a set-equality test between the schema enum and the canonical runtime receipt set. Exercise `validate_spec` with each newly valid value and an unknown value; the unknown must still fail. This preserves the meaning and authority of receipts: a spec reference remains a claim, while receipt validation and fingerprint checks remain in the existing runtime gate.

Do not make a completed gate-valid spec a prerequisite of `grok_change.py start`: `change.start_change()` generates an intentionally incomplete draft with `UNKNOWN` success fields and empty criteria, and gate validation is designed to reject it until scoping. If early validation is desired within this issue, only check the generated document's schema shape, or validate an author-completed spec at an existing transition boundary; do not block initial scaffolding or expand the CLI into a new authority path.

## Acceptance checks

1. The schema enum equals both seven-kind runtime sets, with no eighth alias; `bitrix_review` and `data_review` validate as evidence references and an unknown receipt is rejected.
2. Existing `verification._change_specs()` reaches the same `validate_spec` result for an authored spec; no re-labeling of `data_review` as `code_review` is needed.
3. Initial scaffold creation still succeeds with its draft placeholders. Local receipt issuance, route-required evidence, and external Trust CI authority are unchanged.

Source inspection only; no product code, database, or gate was changed or run for this analysis.
