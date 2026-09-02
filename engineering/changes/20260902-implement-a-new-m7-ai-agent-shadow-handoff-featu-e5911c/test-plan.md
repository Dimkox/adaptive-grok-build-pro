# Test plan — M7 local shadow handoff

| Priority | Scenario | Future evidence |
| --- | --- | --- |
| P0 | Unknown field/version and forbidden remote action fail closed | `test_shadow_contracts.py` |
| P0 | M4 intent/lease packet binds M5 legacy intent while M5 TaskPacket stays a separate field | `test_shadow_contracts.py` |
| P0 | Packet-authority input head and snapshot/result/M6 subject head follow the exact directional equality chain | `test_shadow_contracts.py` |
| P0 | Non-pass, unsupported-pass or contradictory semantic bridge cannot produce a bundle | `test_shadow_contracts.py` |
| P0 | Pure opaque bridge rejects `ready_for_human` and remains blocked pending durable producer lookup | `test_shadow_contracts.py` |
| P0 | Directly forged aggregate is not a valid evaluator input | `test_shadow_evaluation.py` |
| P0 | Duplicate outcome ID or bundle digest is replay | `test_shadow_evaluation.py` |
| P0 | Any safety miss, rollback, escaped defect, duplicate dispatch or unaccounted call blocks | `test_shadow_evaluation.py` |
| P1 | 30 qualifying outcomes produce hand-derived numerators, denominators and millionths | `test_shadow_evaluation.py` |
| P1 | Sample, observation, baseline, quality, budget/deadline and containment failures are deterministic | `test_shadow_evaluation.py` |

Correction TDD observed on `c8b450f…`: two producer-accurate bridge tests failed against the false shared packet/head surface and one forged-aggregate test showed direct authorization. The corrected focused suite must pass bridge mapping, blocked lookup state, schema parity and internal aggregate recomputation. The 30-item cohort remains synthetic algorithm evidence only, not a factual human cohort; final full verification and route reviews remain blocked on dependency restack and final architecture ownership.
