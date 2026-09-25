# Test plan — architecture model path-shape preflight with located diagnostics

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Trailing separator in `repository_paths` is reported once, naming document, line, node, value and reason | `tests/test_architecture_model_preflight.py::TrailingSeparatorTests::test_trailing_separator_yields_one_located_preflight_finding` |
| P0 | Same defect still fails closed (no silent normalization) | `tests/test_architecture_model_preflight.py::TrailingSeparatorTests::test_trailing_separator_is_rejected_not_silently_normalized` |
| P0 | Control: repaired model preflights clean and loads | `tests/test_architecture_model_preflight.py::TrailingSeparatorTests::test_valid_model_preflights_clean_and_loads` |
| P1 | Reason text distinguishes trailing separator / absolute / empty segment / dot segment / backslash | `tests/test_architecture_model_preflight.py::ShapeReasonTests::test_each_shape_defect_gets_its_own_reason` |
| P1 | Rules-document defect is located in `architecture/rules.yaml` | `tests/test_architecture_model_preflight.py::RulesDocumentLocationTests::test_rule_path_defect_names_the_rules_document` |
| P1 | Doctor gate reports one located failure seconds before the suite, passes on the shipped model | `tests/test_architecture_model_preflight.py::DoctorPreflightGateTests` |
| P2 | Preflight degrades to a finding (never raises) when the documents are absent | `tests/test_architecture_model_preflight.py::PreflightRobustnessTests::test_missing_model_is_a_finding_and_never_raises` |

## Automated checks

- Unit: `python3 -m unittest tests.test_architecture_model_preflight` — 15 tests in ~1.7 s, the whole
  located-diagnosis contract in seconds against the 453 s cascade it replaces.
- Integration: neighbouring consumers of `load_architecture()` — `tests.test_architecture_model` (82),
  `tests.test_architecture_fitness` (130), `tests.test_governance` (53), `tests.test_change_receipts`
  (28), `tests.test_verification_doctor` (85), `tests.test_structure` (21), `tests.test_toolchain` (15),
  `tests.test_landing_architecture_boundaries` (4) — then the full root suite and
  `python3 scripts/grok_verify.py --mode pr`.
- Contract: nothing changed — architecture documents, schemas, generated views and governance JSON are
  untouched, so digests must not move.
- E2E: `python3 scripts/grok_doctor.py` on a harness copy with the injected defect must exit 1 and print
  exactly one `architecture-model` line naming `architecture/system.yaml:<line>`.
- Static analysis: `python3 -m ruff check .grok-stack/adaptive_grok scripts tests`, bandit as
  configured, `git diff --check`.

## Manual checks

- Read the emitted diagnostic once against the real shipped model mutated in a private scratch copy and
  confirm the named line is the injected entry. The test does the same thing with an independent line
  oracle (scan for the node id line, then the first literal line after it) rather than reusing the
  implementation's own scanner.
