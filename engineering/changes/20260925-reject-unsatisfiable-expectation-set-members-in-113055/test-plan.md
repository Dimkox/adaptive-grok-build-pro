# Test plan — Reject unsatisfiable expectation-set members in typed specs at plan time

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Exact set with one unproven member is rejected and the finding names that member, criterion id and missing executable mutation/undo probe | `tests/test_spec_expectation_sets.py::ExpectationSetTests::test_dead_member_of_an_exact_set_is_rejected_and_named` |
| P0 | Every exact route-base package keeps an identical full error list (no package is rewritten to satisfy the new rule) | `ExpectationSetTests::test_baseline_and_current_validator_errors_match_for_every_baseline_package` (98 committed base packages) |
| P0 | Nonexistent/pass-only/lookalike/wrong-literal selectors, fake TestCase bases and cross-entry token assembly fail closed | `test_nonexistent_selector_cannot_prove_a_member`, `test_selector_without_the_probe_helper_cannot_prove_a_member`, `test_local_pass_only_helper_lookalike_cannot_prove_a_member`, `test_probe_helper_must_name_the_same_literal_member`, `test_local_testcase_lookalike_is_not_an_executable_selector`, `test_member_name_cannot_be_assembled_across_test_entries` |
| P0 | Upper bound without a non-emptiness assertion is rejected because an empty observation satisfies it | `ExpectationSetTests::test_upper_bound_without_non_emptiness_can_never_fail` |
| P1 | Fully probed declaration and non-empty upper bound both pass | `ExpectationSetTests::test_every_member_with_a_probe_is_accepted`, `test_upper_bound_with_non_emptiness_is_accepted` |
| P1 | Ordinary prose with placeholders, counts, empty groups or JSON literals is not turned into a set | `ExpectationSetTests::test_placeholders_counts_and_code_are_not_expectation_sets` |
| P1 | Only `test` evidence proves liveness; receipt, attestation and production-signal evidence do not | `ExpectationSetTests::test_non_test_evidence_never_proves_liveness` |
| P1 | Cues stay in their sentence, plural allowed-deviations is recognized, and exact `{A, B}` is checked | `test_exactness_cue_does_not_cross_a_sentence_boundary`, `test_plural_allowed_deviations_is_an_upper_bound_cue`, `test_short_members_in_an_exact_multi_member_set_are_not_placeholders` |
| P2 | Malformed criterion shapes are skipped instead of raising | `ExpectationSetTests::test_malformed_criteria_are_skipped_not_crashed` |

## Automated checks

- Unit: `python3 -m unittest tests.test_spec_expectation_sets -q` (31 tests).
- Integration: `python3 scripts/grok_spec.py validate <this package>/change-spec.yaml --gate --json` and the
  path-API rejection test against a temporary repository root.
- Contract: `python3 -m unittest tests.test_change_spec tests.test_governance tests.test_json_schema_subset
  tests.test_demo tests.test_package_status tests.test_verification_doctor tests.test_workflow_artifacts -q`;
  the criterion key set is asserted against the key set the independent holdout pins.
- E2E: `python3 scripts/grok_verify.py --mode pr` on the frozen tree.
- Static analysis: `python3 -m ruff check .grok-stack/adaptive_grok scripts tests` and `git diff --check`.
- Negative control: the original nine mutants remain historical evidence; the repair adds executable
  regressions for every surviving independent-review mutant and reruns both reviews on the frozen successor.

## Manual checks

- `brief.md` records proposal items 2 and 3 as separately routed work and explicitly forbids claiming this
  partial proposal-1 delivery closes issue #202.
