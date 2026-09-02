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

TDD sequence after dependency clearance: RED missing contracts → GREEN frozen bridges/bundle → RED missing cohort evaluator → GREEN bounded aggregate → closed-schema parity → focused/full verification. No product test is claimed by this package-only commit.
