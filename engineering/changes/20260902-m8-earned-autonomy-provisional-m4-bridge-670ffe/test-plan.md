# Test plan — M8 earned autonomy provisional M4 bridge

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | closed records reject missing unknown wrong-version and L3/L4 data | `factory/tests/test_autonomy*.py` |
| P0 | full M7 wire recomputes all digest/equality chains; forged aggregate/evaluation, bundle/outcome mismatch, validator collapse or provider-map mismatch fails | focused unit/schema tests |
| P0 | blocked M7, absent durable acceptance/currentness, fewer than 30 acceptances, mixed tuple, expiry, audit gap or threshold failure blocks promotion | focused unit tests |
| P0 | all eight demotion triggers atomically produce L0/halted | source-only unit tests using synthetic boundary data |
| P1 | exact 30, exact 20% audit and threshold metrics are deterministic but cannot qualify on provisional M7 | source-only unit tests using synthetic boundary data |
| P1 | tuple mutation/expiry prevents reuse; canonical output is stable | focused unit tests |

## Automated checks

- Unit: source-only TDD may proceed under the explicit override; fixtures must be labeled synthetic and cannot become factual evidence.
- Integration: none; design has no persistence or external effects.
- Contract: closed schema plus Python parser conformance.
- E2E: M7→M8 restack, temporary-adapter removal and real cohort qualification, separately gated.
- Static analysis: compile, Ruff, Bandit and root verifier after implementation.

## Manual checks

- Confirm no cohort/example rows, keys, credentials, external calls or activation code are introduced.
