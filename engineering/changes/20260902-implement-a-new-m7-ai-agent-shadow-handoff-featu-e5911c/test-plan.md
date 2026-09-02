# Test plan — M7 local shadow handoff

| Priority | Scenario | Future evidence |
| --- | --- | --- |
| P0 | Unknown field/version and forbidden remote action fail closed | `test_shadow_contracts.py` |
| P0 | Any task/run/fence/packet/manifest/head/verdict/evidence mutation invalidates binding/digest | `test_shadow_contracts.py` |
| P0 | Non-pass, unsupported-pass or contradictory semantic bridge cannot produce a bundle | `test_shadow_contracts.py` |
| P0 | Duplicate outcome ID or bundle digest is replay | `test_shadow_evaluation.py` |
| P0 | Any safety miss, rollback, escaped defect, duplicate dispatch or unaccounted call blocks | `test_shadow_evaluation.py` |
| P1 | 30 qualifying outcomes produce hand-derived numerators, denominators and millionths | `test_shadow_evaluation.py` |
| P1 | Sample, observation, baseline, quality, budget/deadline and containment failures are deterministic | `test_shadow_evaluation.py` |

Observed provisional TDD sequence: RED missing contracts → GREEN frozen bridges/bundle (`9152daf`) → RED missing cohort evaluator → GREEN bounded aggregate (`030a8d7`) → RED missing schemas → GREEN closed-schema parity (`5615933`). The 30-item cohort is synthetic algorithm evidence only, not a factual human cohort. Final full verification and route reviews remain blocked on dependency restack and final architecture ownership.
