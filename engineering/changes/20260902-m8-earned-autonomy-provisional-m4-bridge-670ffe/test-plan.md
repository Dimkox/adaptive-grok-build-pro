# Test plan — M8 earned autonomy provisional M4 bridge

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | closed records reject missing unknown wrong-version and L3/L4 data | future `factory/tests/test_autonomy*.py` |
| P0 | provisional M7, fewer than 30 real acceptances, mixed tuple, expiry, audit gap or threshold failure blocks promotion | future unit tests after block clears |
| P0 | all eight demotion triggers atomically produce L0/halted | source-only unit tests using synthetic boundary data |
| P1 | exact 30, exact 20% audit and threshold boundaries qualify deterministically | source-only unit tests using synthetic boundary data |
| P1 | tuple mutation/expiry prevents reuse; canonical output is stable | future unit tests after block clears |

## Automated checks

- Unit: source-only TDD may proceed under the explicit override; fixtures must be labeled synthetic and cannot become factual evidence.
- Integration: none; design has no persistence or external effects.
- Contract: closed schema plus Python parser conformance.
- E2E: M7→M8 restack and real cohort qualification, separately gated.
- Static analysis: compile, Ruff, Bandit and root verifier after implementation.

## Manual checks

- Confirm no cohort/example rows, keys, credentials, external calls or activation code are introduced.
