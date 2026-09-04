# Test plan — M8 earned autonomy on exact M7 00e0e4f

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Actual-M7 producer reuse, aggregate/evaluation recomputation, one-to-one identity/receipt/head binding, and unavailable acceptance/currentness | `factory/tests/test_autonomy.py` |
| P0 | Minimum real cohort, per-day audit, zero safety tolerance, quality/cost/latency/time/replay gates, one-level L2 cap, separate activation, and deterministic L0 demotion | `factory/tests/test_autonomy.py` |
| P1 | Closed schema parity, offline M7 references, absence of duplicate producer shapes and effect-bearing fields | `factory/tests/test_autonomy_schema.py` and architecture checks |

## Automated checks

- Unit: run the two M8 test modules together after one missing-module RED.
- Integration: pure bridge composition against actual M7 classes/evaluator; run the existing 30 M7 shadow tests only if a compatibility change requires it.
- Contract: resolve both M8 schemas and their six M7 references offline; verify closure, field parity, authority constants, and forbidden fields.
- E2E: none; no runtime or activation surface exists.
- Static analysis: compile imported modules and validate affected architecture, drift, and generated diagram parity.

## Manual checks

- Confirm exact M7 remains the first parent and no predecessor product path changes.
- Do not run PostgreSQL, full factory tests, `grok_verify`, reviews, packaging, network, or any external action.
