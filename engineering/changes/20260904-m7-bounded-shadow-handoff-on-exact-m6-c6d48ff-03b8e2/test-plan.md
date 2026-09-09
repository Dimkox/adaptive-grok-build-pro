# Test plan — M7 bounded shadow handoff on exact M6 c6d48ff

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Producer-accurate M4-M6 bindings, recomputed nested identities, immutable blocked bundle, and absence of operational authority | `factory/tests/test_shadow_contracts.py` |
| P0 | Aggregate recomputation, replay/cohort rejection, fixed sample/quality/safety/budget/containment thresholds, and human-only recommendation | `factory/tests/test_shadow_evaluation.py` |
| P1 | Six-schema closure, local reference resolution, field parity, and architecture ownership | Focused schema and architecture checks |

## Automated checks

- Unit: run the two shadow modules together; canonical expected result is 30 tests.
- Integration: no runtime or PostgreSQL integration exists in this source-only phase.
- Contract: schema resolution, closure, version, enum, field-parity, and forbidden-remote-field assertions are included in the shadow contract module.
- E2E: none; no service or external capability is wired.
- Static analysis: compile the two new Python modules and validate only affected architecture structure/diagram parity.

## Manual checks

- Confirm the exact M6 predecessor remains the first parent and that the canonical diff contributes only the ten named add-only product paths.
- Do not run PostgreSQL, the full factory suite, `grok_verify`, review agents, packaging, or any external action in this bounded phase.
