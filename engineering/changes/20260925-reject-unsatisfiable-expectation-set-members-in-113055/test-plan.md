# Test plan — Reject unsatisfiable expectation-set members in typed specs at plan time

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Exact set with one unproven member is rejected and the finding names that member, the criterion id and the missing liveness proof | `tests/test_spec_expectation_sets.py::ExpectationSetTests::test_dead_member_of_an_exact_set_is_rejected_and_named` |
| P0 | Every recorded historical package keeps an identical validator verdict (no package is rewritten to satisfy the new rule) | `ExpectationSetTests::test_no_existing_package_declares_an_unsatisfiable_set` plus the 106-package before/after sweep |
| P0 | Upper bound without a non-emptiness assertion is rejected because an empty observation satisfies it | `ExpectationSetTests::test_upper_bound_without_non_emptiness_can_never_fail` |
| P1 | Fully probed declaration and non-empty upper bound both pass | `ExpectationSetTests::test_every_member_with_a_probe_is_accepted`, `test_upper_bound_with_non_emptiness_is_accepted` |
| P1 | Ordinary prose with placeholders, counts, empty groups or JSON literals is not turned into a set | `ExpectationSetTests::test_placeholders_counts_and_code_are_not_expectation_sets` |
| P1 | Only `test` evidence proves liveness; receipt, attestation and production-signal evidence do not | `ExpectationSetTests::test_non_test_evidence_never_proves_liveness` |
| P2 | Malformed criterion shapes are skipped instead of raising | `ExpectationSetTests::test_malformed_criteria_are_skipped_not_crashed` |

## Automated checks

- Unit: `python3 -m unittest tests.test_spec_expectation_sets -q` (19 tests).
- Integration: `python3 scripts/grok_spec.py validate <this package>/change-spec.yaml --gate --json` and the
  path-API rejection test against a temporary repository root.
- Contract: `python3 -m unittest tests.test_change_spec tests.test_governance tests.test_json_schema_subset
  tests.test_demo tests.test_package_status tests.test_verification_doctor tests.test_workflow_artifacts -q`;
  the criterion key set is asserted against the key set the independent holdout pins.
- E2E: `python3 scripts/grok_verify.py --mode pr` on the frozen tree.
- Static analysis: `python3 -m ruff check .grok-stack/adaptive_grok scripts tests` and `git diff --check`.
- Negative control: nine mutants of the new rule (rule disabled, member extraction disabled, probe match
  inverted, non-emptiness clause removed, any evidence kind accepted, placeholder filter removed,
  gate-only wiring, warning-only wiring) were each run against the new module; every mutant failed at least
  one test, so the green suite is not vacuous.

## Manual checks

- `brief.md` records the two proposal items of issue #202 that stay out of this contour and why.
