# Test plan — Implement bounded Factory v1.5 result admission contract API

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Real POST/GET return correlated 503 and never touch an exploding store | `factory/tests/test_result_admission_api.py` |
| P0 | Duplicate JSON, identity mismatch, bool fence and secret payload fail closed | focused result tests |
| P1 | V1 and seven unavailable channels remain unchanged/non-consuming | broker and result schema suites |
| P1 | Canonical contracts and architecture ownership remain aligned | OpenAPI/schema/architecture suites |

## Automated checks

- Unit: result contracts and broker tests.
- Integration: real `FactoryService` plus ASGI client and exploding store.
- Contract: JSON Schema/OpenAPI parity and architecture validation/fitness.
- E2E: full Factory discovery, then controller-owned full PR verifier.
- Static analysis: Ruff and `git diff --check`.

## Manual checks

- Confirm no persistence, outbox, dispatch, provider or U4 claims in final diff/report.
