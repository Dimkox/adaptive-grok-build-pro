# Factory v1.5 Fast Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a minimal, runnable Linux factory vertical implementing U0-U3 and U5-U7 from Factory Unified Upgrade v1.5, with U4/macOS explicitly excluded by the owner.

**Architecture:** Add new versioned sidecar contracts instead of mutating closed v1/v2 wire formats. Connect context selection, factual decisions, tool-result sanitization, observation-only prediction, and qualification into the existing factory seams while preserving PostgreSQL, L5 SQLite, and Trust CI authority boundaries.

**Tech Stack:** Python 3 stdlib/dataclasses, FastAPI/Pydantic at existing boundaries, JSON Schema, PostgreSQL forward migrations, unittest/pytest-compatible tests.

**Spec:** `engineering/changes/20260924-factory-unified-upgrade/FACTORY_UNIFIED_UPGRADE_TZ.md` plus `FACTORY_TZ_v1.5_ADDENDUM_BB-01.md`

## Global Constraints

- U4/macOS, Xcode, XCTest, notarization, and Hackintosh are `excluded_by_owner`; never claim Apple acceptance.
- U5 prediction remains observation-only and may report `not_qualified`; it cannot change authority, routing, budgets, checks, or M8.
- Existing closed schemas and execution v1/v2 contracts remain byte-compatible; new semantics use versioned sidecars/envelopes.
- No new service, database, queue, distributed transaction, or GitHub Actions workflow.
- Preserve separate Factory PostgreSQL, L5 SQLite, and Trust CI state/authority.
- Unknown historical time, cost, acceptance, and prediction facts remain unknown, never zero.
- All new persisted changes are additive and forward-fixable; feature activation defaults off.
- The fast release must be runnable and contract-tested, but deferred qualification must remain explicit rather than fabricated as pass.
- BB is an optional default-off execution/observation backend; the factory remains authority, raw unauthenticated BB interfaces are never exposed, and live BB/Workflows/Orchestra qualification may remain `not_run`.

## Review Focus

- Reject path traversal, absolute paths, secret paths, unknown fields, cross-repository facts, and oversized context entries.
- Keep canonical digests deterministic across ordering and serialization.
- Distinguish rejected, unavailable, unknown, and observed outcomes without collapsing them into pass/fail.
- Preserve idempotency for repeated decision/result/qualification imports.
- Prove observation-only ML and excluded Apple scope cannot influence authorization or core acceptance.

---

### Task 1: Admit the v1.5 contract bundle and U0 decision

**Files:**
- Create: `engineering/changes/20260924-factory-unified-upgrade/FACTORY_UNIFIED_UPGRADE_TZ.md`
- Create: `engineering/changes/20260924-factory-unified-upgrade/FACTORY_UPDATE_HANDOFF.md`
- Create: `engineering/changes/20260924-factory-unified-upgrade/implementation-map.json`
- Create: `engineering/changes/20260924-factory-unified-upgrade/delivery-manifest.json`
- Modify: `engineering/changes/20260930-factory-v1-5-fast-working-release-52ad34/*.md`
- Test: `tests/test_factory_v15_bundle.py`

**Interfaces:**
- Consumes: owner-supplied v1.5 spec bytes and repository-backed v1.3 lineage.
- Produces: one hash-bound v1.5 bundle, explicit U4 exclusion, and U0 retain-native/default-off decision.

- [ ] Write tests for version 1.5, 26 unique F IDs, 114 unique AC IDs, S1-S9, U0-U7, exact hashes, U4 exclusion, and no false implementation claim; run and observe failure.
- [ ] Materialize the canonical bundle and U0 decision with exact source/ref/license gaps recorded; run focused tests to green.
- [ ] Commit the admitted bundle and durable change scope.

### Task 2: Versioned context manifest and project-rule binding

**Files:**
- Create: `factory/src/adaptive_factory/context_contracts.py`
- Create: `factory/contracts/jsonschema/context-manifest.v1.schema.json`
- Create: `factory/tests/test_context_contracts.py`
- Modify: `factory/src/adaptive_factory/__init__.py`

**Interfaces:**
- Consumes: repository identity, exact source identity/dirty fingerprint, route domains/paths, rule IDs/revisions, bounded entries.
- Produces: `ContextManifestV1`, canonical `context_digest`, selection reasons, and validated project-rule bindings.

- [ ] Add failing tests for canonical ordering/digest, bounds, unknown fields, path/secret rejection, tenant/repository isolation, and rule identity.
- [ ] Implement strict dataclasses/parsers and schema without network fetch or arbitrary filesystem reads.
- [ ] Run focused and factory contract suites; commit green behavior.

### Task 3: Durable factual decisions, timing, and cost completeness

**Files:**
- Create: `factory/src/adaptive_factory/decision_contracts.py`
- Create: `factory/contracts/v15/decision-record.v1.schema.json`
- Create: `factory/tests/test_decision_contracts.py`
- Modify: `factory/src/adaptive_factory/store.py`
- Create: next available `factory/src/adaptive_factory/resources/0xx_factory_v15_decisions.sql`
- Modify: `factory/tests/test_migrations.py`
- Modify: `factory/tests/test_postgres_integration.py`

**Interfaces:**
- Consumes: run/attempt identity, observed facts, rule/version, source/context digests, outcome/reason, timing and priced/unknown usage.
- Produces: append-only idempotent `DecisionRecordV1`, supersession links, phase timing, and complete/incomplete cost summaries.

- [ ] Add failing unit/migration/integration tests for strict validation, idempotency, supersession, unknown cost, and atomic state+decision behavior.
- [ ] Implement the additive contract and persistence/outbox seam using the existing store transaction.
- [ ] Run focused PostgreSQL-capable checks where available; record unavailable environment facts; commit.

### Task 4: Pre-model tool-result envelope and semantic execution evidence

**Files:**
- Create: `factory/src/adaptive_factory/result_contracts.py`
- Create: `factory/contracts/jsonschema/tool-result-envelope.v1.schema.json`
- Create: `factory/contracts/jsonschema/semantic-execution-evidence.v2.schema.json`
- Create: `factory/tests/test_result_contracts.py`
- Modify: `factory/src/adaptive_factory/brokers.py`
- Modify: `factory/tests/test_brokers.py`

**Interfaces:**
- Consumes: structured results, stdout/stderr, errors, streams, attachments/cache/resume observations and sanitization profile.
- Produces: bounded `allow|redacted|rejected|unavailable` envelope plus candidate/context/criterion/command/result/report binding before model reuse.

- [ ] Add failing tests for every result channel, secret redaction, truncation, unsupported interception, replay identity, and semantic binding.
- [ ] Implement a new envelope/sidecar while retaining existing v1/v2 event readers unchanged.
- [ ] Run protocol/broker/semantic tests and commit.

### Task 5: Observation-only prediction and explanation artifacts

**Files:**
- Create: `factory/src/adaptive_factory/prediction_contracts.py`
- Create: `factory/contracts/jsonschema/prediction-observation.v1.schema.json`
- Create: `factory/contracts/jsonschema/prediction-explanation.v1.schema.json`
- Create: `factory/tests/test_prediction_contracts.py`

**Interfaces:**
- Consumes: pre-check feature snapshot, temporal split metadata, model/background/explainer digests, prediction and contribution vector.
- Produces: `not_qualified|available|unavailable` observation artifacts with additivity validation and no authority output.

- [ ] Add failing tests for leakage timestamps, split identity, unknown labels, additivity tolerance/output space, full vector, and absence of authority fields.
- [ ] Implement deterministic artifact validation without adding an ML runtime dependency; `not_qualified` is a valid result.
- [ ] Run focused tests and commit.

### Task 6: Qualification, handoff, operator surface, and release readiness

**Files:**
- Create: `factory/src/adaptive_factory/qualification.py`
- Create: `factory/contracts/jsonschema/factory-v15-qualification.v1.schema.json`
- Create: `factory/tests/test_qualification.py`
- Modify: `factory/src/adaptive_factory/api.py`
- Modify: `factory/tests/test_api.py`
- Modify: `factory/README.md`
- Modify: `README.md`
- Modify: `START_HERE.md`
- Modify: `PROJECT_STATE.json`
- Modify: `engineering/changes/20260930-factory-v1-5-fast-working-release-52ad34/release.md`

**Interfaces:**
- Consumes: context, decision, result, semantic, prediction, and existing technical/semantic evidence.
- Produces: machine/human qualification summary that distinguishes core accepted, deferred/not-qualified ML, excluded Apple, M8 inactive, and external Trust CI pending.

- [ ] Add failing contract/API tests for honest status composition, missing evidence, U4 exclusion, default-off optional adapters, and non-authoritative local release state.
- [ ] Implement read-only qualification/API presentation and update operator/bootstrap/state documentation.
- [ ] Run focused suites, full `python3 scripts/grok_verify.py --mode pr`, route reviews, and release-readiness audit; commit only current evidence.

### Task 7: BB-01 optional backend boundary

**Files:**
- Create: `engineering/changes/20260924-factory-unified-upgrade/FACTORY_TZ_v1.5_ADDENDUM_BB-01.md`
- Create: `factory/src/adaptive_factory/bb_contracts.py`
- Create: `factory/contracts/jsonschema/bb-backend-profile.v1.schema.json`
- Create: `factory/tests/test_bb_contracts.py`

**Interfaces:**
- Consumes: factory task/run/attempt/lease/context/policy identities and BB capability observations.
- Produces: a default-off `BBBackendProfileV1` and lifecycle/effect observation contract; it does not install, activate, or qualify BB.

- [ ] Add failing tests for default-off behavior, identity ownership, idempotency-key conflicts, command/ack/effect separation, unknown stop outcome, finite budgets, and `not_run` qualification.
- [ ] Implement only the thin strict contract and native fallback; do not expose raw unauthenticated BB API, add a service, or claim live support.
- [ ] Bind BB-01 into the v1.5 bundle/map/manifest and qualification summary; run focused tests and commit.
