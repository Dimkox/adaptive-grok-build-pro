# Issue #162 implementation evidence

The first incorrect state was the five-value enum at `schemas/change-spec.schema.json:17`; both runtime registries already include `bitrix_review` and `data_review` (`.grok-stack/adaptive_grok/receipts.py:42` and `workflow_artifacts.py:36`). The repair adds only those two existing names. `tests/test_change_spec.py` now checks exact parity with both registries, validates a complete spec for every runtime kind, and rejects an unknown kind.

Regression-first run: `python3 -m unittest discover -s tests -p test_change_spec.py -v` exited 1 before the schema edit. Its three observed failures were parity missing `bitrix_review` and `data_review`, plus validation errors for each name. Raw output: `/home/pall/.cache/agbp-run/issues-wave-20260921/issue162/red-test-change-spec.log`.

After the schema edit, the same command exited 0 (`Ran 33 tests ... OK`). `python3 -m unittest discover -s tests -p test_workflow_artifacts.py -v` exited 0 (`Ran 24 tests ... OK`). `git diff --check` exited 0. Raw green outputs: `/home/pall/.cache/agbp-run/issues-wave-20260921/issue162/green-test-change-spec.log` and `/home/pall/.cache/agbp-run/issues-wave-20260921/issue162/green-test-workflow-artifacts.log`.

This is additive schema compatibility. Receipt issuance, route-required evidence, and external Trust CI authority are unchanged. No migration or live operation is involved. The coordinator still owns full PR verification, independent reviews, receipts, and delivery.

## Shipped-validator review follow-up

The independent code review found two further source allowlists with the old five-kind vocabulary: `trust-ci/src/adaptive_trust_ci/runner.py:32` and `trust-ci/holdout.example/change_spec_validate.py:27`. These independently validate references during metadata extraction and example holdout validation. Only those source allowlists were widened to the same seven known kinds; no validator imports candidate runtime code during validation.

Four new tests exercise `extract_spec_metadata()` and `_validate_document()` directly, compare each validator's allowlist with the schema and both runtime registries, accept `bitrix_review` and `data_review`, and reject `unknown_review`. Before the source edits, the four-test command exited 1: two parity failures and four subtest errors, all caused by those two missing names. Afterward it exited 0 (`Ran 4 tests ... OK`). The adjacent pinned command `PYTHONPATH=trust-ci/src:trust-ci/tests python3 -m unittest -v test_runner test_change_spec_holdout` exited 0 (`Ran 45 tests ... OK`), and `git diff --check` exited 0. Raw logs: `/home/pall/.cache/agbp-run/issues-wave-20260921/issue162/red-trust-ci-vocabulary.log`, `green-trust-ci-vocabulary.log`, and `green-trust-ci-runner-holdout.log` in the same directory.

These results establish checked-in source consistency only. The deployed Trust CI worker and server-mounted holdout are outside this branch and have not been changed or tested here. Rollout of those deployed components remains a separate reviewed and authorized operation; the external exact-head check remains merge authority. The prior review reports describe the earlier schema-only tree and need renewal after this follow-up.
