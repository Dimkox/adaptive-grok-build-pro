# Test plan — Реализовать Factory v1.5 F24 F26 paired A/B/C qualification harness: frozen 12-case corpus, Pump Selector fixtures/oracle, behavior impact selector, immutable baseline, thresholds, budgets and deterministic tests

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Missing/tampered corpus or baseline, confounded pins, missing required attempt, wrong pump document/curve, unknown coerced to zero | focused unit tests fail closed |
| P0 | Critical domain regression despite lower latency/cost | verdict remains fail |
| P1 | Units normalization, finite budgets, unknown usage, impact selection | deterministic focused unit tests |

## Automated checks

- Unit: `python3 -m unittest factory.tests.test_behavior_qualification`
- Integration: package resource loading plus injected deterministic A/B/C executor.
- Contract: closed input/output contracts and stable canonical digest.
- E2E: focused module runs all 36 mode/case observations without provider access.
- Static analysis: `python3 -m compileall factory/src/adaptive_factory factory/tests/test_behavior_qualification.py`.

## Manual checks

- No live provider or production effects are permitted in this contour.
