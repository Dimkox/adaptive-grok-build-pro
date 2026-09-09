# Test plan — M9 staged delivery on corrected exact M8 a937ac8

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Closed signed bindings, actual-M8 recomputation, no caller authority, stale/replay/order/nonfinite rejection, and human production boundary | `delivery/tests/test_contracts.py`, `test_m8_boundary.py`, `test_evaluator.py` |
| P0 | Locked one-step dry run, at-most-once concurrent recording, 128-entry bounds, expiry recheck, full digest chain, and production unreachable | `delivery/tests/test_controller.py` |
| P0 | Recovery only halts, decrements one authorized exposure, or restores the exact prior signed artifact | `delivery/tests/test_recovery.py` |
| P1 | Package/import isolation and truthful architecture/project documentation | package metadata and architecture checks |

## Automated checks

- Unit: run the seven delivery test files as one focused suite after one missing-package RED.
- Integration: compose the M9 handoff with actual `adaptive_factory.autonomy` records and the sealed fake adapter only.
- Contract: verify closed immutable fields, exact digest/time/resource bindings, bounded sequences, and absent operational surface.
- E2E: synthetic in-memory preview through last canary; production remains deliberately unreachable.
- Static analysis: compile M9 modules/tests, validate architecture and generated diagram parity, and check predecessor migration/source preservation.

## Manual checks

- Do not run PostgreSQL, full factory tests, `grok_verify`, final reviews, packaging, network, provider calls, or external actions in this source phase.
- A previously passed group is not rerun; only a failed method or the smallest affected group may be repeated.
