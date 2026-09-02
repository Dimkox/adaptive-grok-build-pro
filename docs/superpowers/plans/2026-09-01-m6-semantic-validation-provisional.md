# M6 Provider-Independent Semantic Validation Provisional Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and locally verify the stable provider-independent M6 contract, adjudication, bounded repair and current-doc connectivity layer on exact M4 without inventing M5 runtime behavior.

**Architecture:** Immutable strict parsers mirror five public closed schemas. Pure adjudication derives an exact-state verdict; pure repair emits same-original-writer/fresh-context directives only for cycles `1..3`; docs/tests preserve the factual M4→blocked M5→provisional M6→roadmap-only M7-M9 graph.

**Tech Stack:** Python 3.11 standard library, frozen dataclasses, JSON Schema Draft 2020-12, `unittest`, canonical SHA-256 JSON.

**Spec:** `docs/superpowers/specs/2026-09-01-m6-semantic-validation-provisional-design.md`

**Connectivity:** [README](../../../README.md) ↔ [roadmap](../../../DARK_FACTORY_ROADMAP.md) ↔ [design](../specs/2026-09-01-m6-semantic-validation-provisional-design.md) ↔ this plan ↔ [package](../../../engineering/changes/20260901-m6-provider-independent-semantic-validation-prov-82aac8/brief.md) / [release](../../../engineering/changes/20260901-m6-provider-independent-semantic-validation-prov-82aac8/release.md) / [rollback](../../../engineering/changes/20260901-m6-provider-independent-semantic-validation-prov-82aac8/rollback.md) / [evidence](../../../engineering/changes/20260901-m6-provider-independent-semantic-validation-prov-82aac8/evidence/README.md).

## Global Constraints

- Exact provisional base `94fc5ad878e6b15df6418303caada49a3b93bf4c`; deadline `2026-09-08T00:00:00+03:00` is planning only.
- No M4 SQL/store/state/API/OpenAPI/service or provider/systemd/network/credential/external-write behavior.
- Every product behavior starts with observed RED; collections are sorted, unique, capped at 256; decisions/digests are deterministic.
- No reviewers, receipts, push, PR, merge, deployment or full-M6 claim in this dispatch.

### Task 1: Closed semantic contracts and schemas

**Files:** create `factory/src/adaptive_factory/semantic_contracts.py`, five `factory/contracts/jsonschema/semantic-*.v1.schema.json`/`repair-directive.v1.schema.json`, and `factory/tests/test_semantic_contracts.py`.

**Interfaces:** `RequirementRefV1`, `ValidatorIdentityV1`, `SemanticSubjectV1`, `SemanticFindingV1`, `SemanticCoverageV1`, `SemanticVerdictV1`, `RepairDirectiveV1`; strict `from_dict`; canonical `digest`; finding `identity_digest`.

- [ ] Write tests for closed fields/version/bounds, schema closure, kinds, sorting/uniqueness, key-order digest stability, prose-insensitive identity, exact coverage and validator capabilities.
- [ ] Run RED: `cd factory && uv run python -m unittest tests.test_semantic_contracts -v`; expect missing module.
- [ ] Implement minimal frozen parsers using existing `ContractError`/canonical helpers, and matching schemas; caller never supplies derived identities.
- [ ] Run GREEN with the same command; expect all pass.
- [ ] Update ledger and commit `feat(factory): add M6 semantic contracts`.

### Task 2: Deterministic adjudication

**Files:** create `factory/src/adaptive_factory/semantic_adjudication.py`, `factory/tests/test_semantic_adjudication.py`.

**Interfaces:** `adjudicate(subject, findings, coverages) -> SemanticVerdictV1`.

- [ ] Test pass/repair/needs-human precedence, permutations, duplicate/correlation/contradiction/unsupported-pass outputs, exact coverage, provider-decision rejection, separation and all relevant mutations.
- [ ] Run RED: `cd factory && uv run python -m unittest tests.test_semantic_adjudication -v`; expect missing module.
- [ ] Implement subject-binding validation, deterministic grouping and `needs_human > repair > pass`; no transition method.
- [ ] Run GREEN plus contract suite.
- [ ] Update ledger and commit `feat(factory): adjudicate semantic evidence`.

### Task 3: Pure bounded repair

**Files:** create `factory/src/adaptive_factory/semantic_repair.py`, `factory/tests/test_semantic_repair.py`.

**Interfaces:** `plan_repair(...) -> RepairPolicyDecision(decision, reason, directive)`.

- [ ] Test cycle 1/2/3 directives and cycle zero/four, prose-mutated recurrence, risk/diff/architecture/authority/base/budget/deadline/stale-verdict/writer/context/non-repair escalations.
- [ ] Run RED: `cd factory && uv run python -m unittest tests.test_semantic_repair -v`; expect missing module.
- [ ] Implement ordered pure guards and emit a directive only when all pass.
- [ ] Run all three focused suites GREEN.
- [ ] Update ledger/decision and commit `feat(factory): bound semantic repair cycles`.

### Task 4: Current docs and graph parity

**Files:** modify `README.md`, `factory/README.md`, `DARK_FACTORY_ROADMAP.md`, `tests/test_structure.py`, `tests/test_architecture_model.py`, package docs.

**Interfaces:** docs expose bidirectional README↔roadmap↔spec/plan/package/release/rollback/evidence links and contract graph M4 exact evidence ↔ BLOCKED M5 bridge ↔ M6 contracts ↔ roadmap-only M7 shadow bundle ↔ M8 trust/demotion ↔ M9 signed artifact/canary/recovery.

- [ ] Add failing structure/architecture tests for all current paths, contract filenames, nodes/edges, blocked/full-completion disclaimers and M7-M9 authority ceilings.
- [ ] Run RED: `python3 -m unittest tests.test_structure tests.test_architecture_model -v`; expect missing M6 connectivity/graph text.
- [ ] Update current docs only. Define producer/consumer digests/SHA, mutation invalidation, rollback, and forbidden authority; keep M7-M9 roadmap-only and current ceiling L2/human production.
- [ ] Run GREEN with the same command and M6 focused suites.
- [ ] Update ledger and commit `docs(factory): map provisional M6 dependencies`.

### Task 5: Fresh provisional verification

**Files:** update package `requirements.md`, `tasks.md`, `implementation-ledger.md` only.

- [ ] Run all M6 focused suites, structure/architecture suites, `git diff --check`, and parse all five schemas with `python3 -m json.tool`.
- [ ] Compare diff to exact base; confirm no M4 runtime/API/SQL/provider changes.
- [ ] Mark only pure-slice items complete and keep M5/M7-M9 items BLOCKED/roadmap-only.
- [ ] Commit `docs(factory): bind M6 provisional evidence`; do not transition full change ready or create receipts.

## Plan self-review

All M6-001..012 map to exact tests/tasks; names and types are consistent; each product step has RED before code. No placeholder/fabricated M5 component exists. Inline execution is explicitly approved; no subagent/reviewer wave is used.
