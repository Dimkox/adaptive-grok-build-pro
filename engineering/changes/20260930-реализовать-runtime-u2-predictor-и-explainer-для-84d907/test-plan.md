# Test plan — Реализовать runtime U2 predictor и explainer для Factory v1.5: data assembly, bounded training/prediction pilot, versioned model artifact, SHAP-style observation-only explanation, deterministic tests; без authority effect

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Future feature or cross-partition change is rejected; authority remains none | `factory/tests/test_prediction_runtime.py` |
| P0 | Same input/seed yields identical artifact and full additive explanation | `factory/tests/test_prediction_runtime.py` |
| P1 | Insufficient/one-class history is explicit and nonblocking | `factory/tests/test_prediction_runtime.py` |
| P1 | Temporal and per-project metrics include baseline and model | `factory/tests/test_prediction_runtime.py` |

## Automated checks

- Unit: focused prediction runtime and existing prediction contract suites.
- Integration: complete factory unittest discovery.
- Contract: existing prediction JSON schemas and semantic contract checks.
- E2E: not applicable; no live model activation or provider path.
- Static analysis: repository PR verifier.

## Manual checks

- None; this contour has no live activation or external effect.
