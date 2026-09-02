# M6 M5-Aligned Semantic Validation Implementation Plan

> **For agentic workers:** execute task-by-task with `superpowers:test-driven-development`, `superpowers:systematic-debugging`, and `superpowers:executing-plans` or `superpowers:subagent-driven-development`. Keep one write owner.

**Goal:** Complete the bounded M6 source implementation against exact M5 candidate `141e51e75b2bb337fa3bb1544639c6c46c287309`, while preserving exact M5 result meanings and independent validator/adjudicator authority.

**Architecture:** A strict bridge converts a fully verified immutable M5 result bundle plus separately authenticated missing inputs into the existing semantic subject. Migration 014 stores append-only subjects/evidence/verdicts/directives behind disjoint least-privilege roles. Service/API layers expose bounded contract-first operations. Repair proposals are finite, same-writer, fresh-context, fenced to exact parent facts, and never provider/application-write authority.

**Tech stack:** Python 3.11, frozen dataclasses, canonical SHA-256 JSON, JSON Schema Draft 2020-12, FastAPI/OpenAPI, PostgreSQL additive migrations, `unittest`.

**Spec:** `docs/superpowers/specs/2026-09-01-m6-semantic-validation-provisional-design.md`

**Connectivity:** [README](../../../README.md) ↔ [roadmap](../../../DARK_FACTORY_ROADMAP.md) ↔ [design](../specs/2026-09-01-m6-semantic-validation-provisional-design.md) ↔ this plan ↔ [package](../../../engineering/changes/20260901-m6-provider-independent-semantic-validation-prov-82aac8/brief.md) / [release](../../../engineering/changes/20260901-m6-provider-independent-semantic-validation-prov-82aac8/release.md) / [rollback](../../../engineering/changes/20260901-m6-provider-independent-semantic-validation-prov-82aac8/rollback.md) / [evidence](../../../engineering/changes/20260901-m6-provider-independent-semantic-validation-prov-82aac8/evidence/README.md).

## Global constraints

- Phase A merge HEAD is `c398ea06daa635ad679e22c8cd29dbf74d2ae12c`; later M4 -> M5 -> M6 restack remains mandatory.
- Migration 013 is source-frozen. Add 014+ only; never touch a shared database.
- M5 `ready_for_human`, `failure_class`, `failure_reason`, infrastructure attempts, and `repair_count` keep their meanings.
- No live model/provider/Git/Trust CI/human-approval/external/production action; no secrets, raw provider bodies, PII, or chain-of-thought.
- Every behavioral slice starts with observed RED, ends with focused GREEN, ledger update, and a small local commit.
- Full `grok_verify`, review wave, receipts, push/PR/merge and external checks are parent finalization tasks.
- Deadline `2026-09-08T00:00:00+03:00` never waives evidence or dependency order.

### Task 0: Phase A factual M5 alignment

**State:** complete at merge `c398ea06daa635ad679e22c8cd29dbf74d2ae12c`.

- [x] Normal local merge of exact M5 `141e51e...`; expected conflicts resolved preserving complete M5 and M6 source/contracts/docs.
- [x] Architecture inventory is 22 nodes, 24 edges, 15 public contracts and 26 rules; README K22 is 22 nodes/231 unique edges.
- [x] Focused M5 35/35, M6 25/25, root structure/architecture/installer 87/87, architecture commands and diff checks pass.

### Task 1: Exact M5 -> semantic bridge

**Files:** add `factory/src/adaptive_factory/semantic_bridge.py`, bridge JSON schema(s), and `factory/tests/test_semantic_bridge.py`; update contract inventory.

- [x] RED: require closed `SemanticExecutionBindingV1`/`SemanticValidationInputsV1`, complete task/run/fence/packet/manifest/snapshot/result/evidence binding, and rejection of every substituted field.
- [x] Include exact terminal proposal and artifact-attestation identities from verified material; never reconstruct them from the aggregate digest alone.
- [x] Require writer + `ready_for_human`; preserve failed-result facts and reject semantic reinterpretation.
- [x] Require separately authenticated holdout/review/typed-requirement/risk/diff-limit/writer-context facts; exact AC set equals packet acceptance IDs.
- [x] Derive the existing `SemanticSubjectV1` deterministically and prove mutation/digest stability.
- [x] GREEN: bridge + existing contract/adjudication/repair tests; update ledger and commit.

### Task 2: Migration 014 and capability-shaped persistence

**Files:** add `factory/src/adaptive_factory/resources/014_semantic_validation_bridge.sql`, update migration/installer tests, store capability classes, and semantic PostgreSQL tests.

- [x] RED static tests: contiguous 014, no rewrite/drop/cascade/broad grants, fixed `search_path`, roles/functions/tables/metrics declared.
- [x] RED disposable PostgreSQL tests when host exists: exact subject replay, divergent replay rejection, cross-run/digest/status/head substitution rejection, immutable evidence, direct DML denial, and role separation.
- [x] Add append-only subject/assignment/finding/coverage/verdict/directive/child-proposal/recovery records with exact redundant M5 bindings and idempotency request digests.
- [x] Add separate coordinator, validator, and adjudicator NOLOGIN/NOINHERIT roles; runtime/public have no semantic table DML and validator cannot adjudicate or finalize execution.
- [x] Add narrowly shaped store methods and exact canonical row verification. No live migration is applied.
- [x] GREEN focused migration/store/PostgreSQL tests; report honestly if disposable PostgreSQL is unavailable; update ledger and commit.

### Task 3: Deterministic service and API integration

**Files:** update semantic service/store, `api.py`, `server.py` if necessary, OpenAPI, JSON schemas, API/server tests.

- [x] RED contract tests for additive subject publish/read, assignment-bound finding/coverage, adjudication, exact verdict read, auth/repository isolation, idempotency, and closed request/response shapes.
- [x] Preserve legacy/M5 endpoints and statuses; do not expose raw provider/prompt/log/secret/source bodies.
- [x] Use semantic-specific scopes/capability stores. A writer or `task:execute` caller cannot append validator evidence or a verdict.
- [x] Recompute verdict from persisted canonical evidence before append; surface contradiction and unsupported-pass outcomes exactly.
- [x] Keep operation/schema inventory closed and architecture edges owned; update ledger and commit after GREEN.

### Task 4: Bounded repair child proposal lifecycle

**Files:** extend semantic repair/store/service/contracts/tests and migration 014 functions only where Task 2 reserved the schema.

- [ ] RED cycles 1..3 exact replay, cycle four, recurrence, wrong writer, reused context, changed base/architecture/authority/head, stale fence/result, risk/diff/budget/deadline escalation.
- [ ] Persist parent task/run/fence/packet/manifest/result, original writer, new context, evidence identities, cycle budget/deadline, proposal state, and typed escalation.
- [ ] Create at most one child proposal per parent/cycle and hand it to an explicit M5 execution broker; M6 never invokes a provider or writes a workspace.
- [ ] A child result creates a new exact subject/evidence cycle; no old verdict survives source/SHA/digest mutation.
- [ ] GREEN lifecycle/concurrency/replay tests; update ledger and commit.

### Task 5: Restart, metrics, installer, architecture, and current docs

**Files:** recovery/service/store/metrics tests, installer/migration docs, architecture model/diagrams, README/factory README/roadmap/package.

- [ ] RED bounded keyset recovery for incomplete assignment/evidence/adjudication/repair states and restart replay without duplicate verdict/child.
- [ ] Add only fixed low-cardinality metrics for decision, escalation reason class, lifecycle state, and recovery outcome.
- [ ] Verify migration/install/uninstall source symmetry and least privilege; no shared DB/system action.
- [ ] Update the factual architecture inventory, source ownership, contracts, edges, package ledger, roadmap status, rollback/forward recovery, and exact test evidence.
- [ ] GREEN all focused M5+M6, architecture/structure/installer, contract/schema/OpenAPI, SQL/static and available disposable PostgreSQL suites; `git diff --check`.
- [ ] Commit bounded source completion without claiming acceptance, M7 compatibility, Trust CI, release, or external delivery.

## Checkpoints and handoff

After each task, send the parent exact commit SHA, RED failure, GREEN count, remaining blockers, and whether any PostgreSQL scenario was skipped. Stop only the dependent slice for an irreconcilable contract conflict; continue independent work. Parent performs final full verification/reviews and dependency-ordered restack/acceptance.
