# M8 Earned Autonomy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development. Execute inline with the route-selected sole `ai_implementer`; no second writer or subagent is permitted.

**Goal:** Build closed recommendation-only M8 contracts and a deterministic fail-closed evaluator after the factual-evidence block clears.

**Architecture:** `autonomy.py` owns immutable M8 parsing/evaluation. Until M7 ancestry is restacked, temporary `m7_autonomy_wire.py` validates the exact `4df2516` producer wire without importing authority; two closed JSON Schemas freeze the boundaries. No persistence, API, event, key, network or external action exists.

**Tech Stack:** Python 3.11 standard library, `unittest`, JSON Schema document.

**Spec:** `docs/superpowers/specs/2026-09-02-m8-earned-autonomy-design.md`

## Global Constraints

- Exact provisional base `9fe779ab9f90719201acfd01160d3452658ff075`; route `670ffe5522e0`.
- The explicit 2026-09-02 user override permits Tasks 1–3 as pure local source work against exact M7 `4df2516` wire identities and clearly labeled synthetic fixtures. Activation, completion, factual cohort qualification, profile issuance/acceptance and external effects still require factual accepted/current M7 restack and >=30 real human acceptances.
- The temporary wire adapter must be removed, not retained as a second producer implementation, when factual M7 ancestry and durable lookup become available.
- `low_risk_text_only` only; audit >=20% and >=1 sample/day; complete bounded non-PII data.
- L2 ceiling; L3/L4 unreachable; recommendation only; no activation, external write, merge, key, secret, persistence or fabricated cohort.

### Task 1: Closed contracts

**Files:** create `factory/tests/test_autonomy.py`, `factory/tests/test_autonomy_schema.py`, `factory/src/adaptive_factory/autonomy.py`, temporary `factory/src/adaptive_factory/m7_autonomy_wire.py`, and the two M8 JSON Schemas.

**Interfaces:** produce the six exact `*V1` records named in the design, each with `from_dict()` and canonical `to_dict()` behavior.

- [ ] Write import and behavior tests that assert closed/versioned/bounded inputs, unsupported class/level and incomplete data fail.
- [ ] Run `PYTHONPATH=factory/src python3 -m unittest factory.tests.test_autonomy factory.tests.test_autonomy_schema -v`; observe missing-symbol RED.
- [ ] Implement minimal immutable records, canonical digest helpers and the closed schema.
- [ ] Re-run the focused command and observe GREEN.
- [ ] Commit the contract slice.

### Task 2: Cohort qualification and promotion

**Files:** modify `factory/tests/test_autonomy.py`, `factory/src/adaptive_factory/autonomy.py`.

**Interfaces:** produce `evaluate_autonomy(cohort, existing_profile, evaluated_at) -> tuple[AutonomyProfileV1, PromotionRecommendationV1]`.

- [ ] Add literal-boundary tests for exact 30 acceptances, distinct identities, factual M7, threshold equality, exact 20% audit, one/day, tuple expiry/mutation and each individual gate failure.
- [ ] Run focused tests and observe RED because evaluation is absent.
- [ ] Implement bounded integer aggregation, deterministic nearest-rank p95 and one-level L0→L1→L2 recommendation.
- [ ] Re-run focused tests and observe GREEN.
- [ ] Commit the evaluator slice.

### Task 3: Atomic demotion

**Files:** modify `factory/tests/test_autonomy.py`, `factory/src/adaptive_factory/autonomy.py`.

**Interfaces:** produce `demote_profile(profile, task, observed_at) -> tuple[AutonomyProfileV1, DemotionDecisionV1]`.

- [ ] Add a table-driven test for the fixed eight-trigger priority and halted follow-up behavior.
- [ ] Run it and observe RED because demotion is absent.
- [ ] Implement the immutable pair with L0, halt=true and external action false.
- [ ] Re-run focused tests and observe GREEN.
- [ ] Commit the demotion slice.

### Task 4: Integration documentation (parent-owned after factual restack)

**Files:** later modify `architecture/system.yaml`, `README.md`, `DARK_FACTORY_ROADMAP.md`, `factory/README.md`, `tests/test_structure.py`, and this package ledger. The bounded correction does not touch root release identity or receipts.

**Interfaces:** register the additive schema and M4→M9 dependency/authority boundaries without adding runtime edges.

- [ ] Add structure expectations first and observe focused structure RED.
- [ ] Update architecture/docs, preserving the complete graph and historical evidence.
- [ ] Run focused autonomy, architecture and structure tests.
- [ ] Commit integration parity.

### Task 5: Local handoff

- [ ] Run fresh focused tests, compile the module, inspect `git diff --check`, and obtain exact SHAs with `git rev-parse`.
- [ ] Parent owns later verification, independent reviews, receipts, push, PR and external Trust CI; do not perform them here.
