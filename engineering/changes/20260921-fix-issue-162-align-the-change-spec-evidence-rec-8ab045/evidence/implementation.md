# Issue #162 implementation evidence

The first incorrect state was the five-value enum at `schemas/change-spec.schema.json:17`; both runtime registries already include `bitrix_review` and `data_review` (`.grok-stack/adaptive_grok/receipts.py:42` and `workflow_artifacts.py:36`). The repair adds only those two existing names. `tests/test_change_spec.py` now checks exact parity with both registries, validates a complete spec for every runtime kind, and rejects an unknown kind.

Regression-first run: `python3 -m unittest discover -s tests -p test_change_spec.py -v` exited 1 before the schema edit. Its three observed failures were parity missing `bitrix_review` and `data_review`, plus validation errors for each name. Raw output: `/home/pall/.cache/agbp-run/issues-wave-20260921/issue162/red-test-change-spec.log`.

After the schema edit, the same command exited 0 (`Ran 33 tests ... OK`). `python3 -m unittest discover -s tests -p test_workflow_artifacts.py -v` exited 0 (`Ran 24 tests ... OK`). `git diff --check` exited 0. Raw green outputs: `/home/pall/.cache/agbp-run/issues-wave-20260921/issue162/green-test-change-spec.log` and `/home/pall/.cache/agbp-run/issues-wave-20260921/issue162/green-test-workflow-artifacts.log`.

This is additive schema compatibility. Receipt issuance, route-required evidence, and external Trust CI authority are unchanged. No migration or live operation is involved. The coordinator still owns full PR verification, independent reviews, receipts, and delivery.
