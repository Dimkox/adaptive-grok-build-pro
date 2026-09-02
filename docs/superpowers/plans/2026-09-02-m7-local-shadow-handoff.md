# M7 Local Shadow Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a closed immutable provider-independent local M7 shadow handoff and bounded cohort evaluator with no external-write surface.

**Architecture:** A pure contract module validates explicit M4/M5/M6 transport bridges and emits only a frozen `blocked_pending_durable_lookup` bundle. A separate evaluator recomputes bounded non-PII outcome aggregates for one exact trust tuple and returns stable failures or an L2 human-review recommendation. M4 runtime/store/service wiring stays absent.

**Tech Stack:** Python 3.11 frozen dataclasses, standard-library JSON/SHA-256, JSON Schema 2020-12, `unittest`, `uv --frozen`.

**Spec:** `docs/superpowers/specs/2026-09-02-m7-local-shadow-handoff-design.md`

## Global Constraints

- Exact local M4 base: `9fe779ab9f90719201acfd01160d3452658ff075`.
- Current field-shape references are M5 `cbfca6550acaa50508eec5829df2724093e32076` and M6 `534b66753ca865974d520f60103b3a18292295ba`; both remain provisional and are never serialized as acceptance authority.
- Output is only `blocked_pending_durable_lookup`; maximum cohort recommendation is `eligible_for_human_l2_review`.
- No service/API/store/migration, provider, network, credential, push, PR, merge, release or deploy surface.
- Hard deadline `2026-09-08 00:00 UTC+3` never waives a gate.
- Pure contract/evaluator source may proceed against opaque bridge values only as non-authoritative transport. Activation, completion and durable/runtime integration are **BLOCKED** until exact accepted M5/M6 ancestry and canonical producer bodies are independently loaded and recomputed.
- Every M5/M6 SHA change pauses downstream writes until a three-way path-overlap and field-level contract-compatibility audit/restack is recorded.

---

### Task 1: Closed bridge and bundle contracts

**Files:**
- Create: `factory/src/adaptive_factory/shadow_contracts.py`
- Create: `factory/tests/test_shadow_contracts.py`

**Interfaces:**
- Consumes: canonical primitives and `ContractError` from `adaptive_factory.contracts`.
- Produces: three predecessor bridges, task evidence, operator proposal, bundle and typed failures.

- [x] **Step 1: Audit current provisional dependencies**

M5 `cbfca655…` defines the provisional TaskPacket, RunManifest, WorkspaceSnapshot and WorkspaceResult surfaces; M6 `534b667…` preserves the provisional envelope, execution binding, validation-inputs, subject, evidence-set and verdict surfaces byte-for-byte from `87897ff…`. The audit consumes only those observable field names and relationships: M4 intent/lease packet binds `legacy_intent_digest`, M5 TaskPacket stays separate, packet authority equals snapshot input, and snapshot result equals WorkspaceResult and M6 subject head. Exact dependency acceptance remains an external ledger fact and activation stays blocked.

- [x] **Step 2: Write failing tests**

Cover unknown versions/fields, rejection of invented dependency/product/evidence fields, directional task/run/fence/packet/head bindings, exact closed pass verdict, blocked lookup state, frozen values, digest mutation and forbidden push/URL/command/credential/auto-merge fields.

- [x] **Step 3: Run RED**

Run: `cd factory && uv run --frozen python -m unittest tests.test_shadow_contracts -v`  
Expected: import failure for missing `adaptive_factory.shadow_contracts`.

- [x] **Step 4: Implement minimal contracts and run GREEN**

Use closed constructors, bounded parsers, tuples, frozen dataclasses and domain-separated digests. Rerun the same command; expect all tests to pass.

- [x] **Step 5: Commit**

Commit: `feat(factory): add immutable M7 shadow bundle contracts`.

### Task 2: Bounded outcome and evaluator

**Files:**
- Modify: `factory/src/adaptive_factory/shadow_contracts.py`
- Create: `factory/src/adaptive_factory/shadow_evaluation.py`
- Create: `factory/tests/test_shadow_evaluation.py`

**Interfaces:**
- Consumes: bundle/cohort digests and closed outcomes.
- Produces: `aggregate_shadow_cohort` and `evaluate_shadow_cohort`.

- [x] **Step 1: Write failing aggregate tests**

Use 30 literal accepted fixtures with hand-derived counts/millionths, then mutate replay, tuple, sample, observation, baseline, quality, safety, budget/deadline and containment cases.

- [x] **Step 2: Run RED**

Run: `cd factory && uv run --frozen python -m unittest tests.test_shadow_evaluation -v`  
Expected: missing evaluator import.

- [x] **Step 3: Implement and run GREEN**

Reject empty/>10,000 cohorts, duplicate outcome/bundle identity, tuple mismatch and direct aggregate input; recompute integer counts, exact millionths, nearest-rank p95 and median from the cohort; sort failures; never emit promotion/merge actions. Run both M7 test modules.

- [x] **Step 4: Commit**

Commit: `feat(factory): evaluate bounded M7 shadow cohorts`.

### Task 3: Closed public schemas

**Files:**
- Create: `factory/contracts/jsonschema/m7-predecessor-bridges.v1.schema.json`
- Create: `factory/contracts/jsonschema/shadow-task-evidence.v1.schema.json`
- Create: `factory/contracts/jsonschema/operator-handoff-proposal.v1.schema.json`
- Create: `factory/contracts/jsonschema/ready-for-pr-bundle.v1.schema.json`
- Create: `factory/contracts/jsonschema/shadow-outcome.v1.schema.json`
- Create: `factory/contracts/jsonschema/shadow-cohort.v1.schema.json`
- Modify: `factory/tests/test_shadow_contracts.py`

**Interfaces:** Python v1 field/enum parity and closed Draft 2020-12 schemas.

- [x] **Step 1: Add failing schema inventory/parity tests**

Assert exact file set, dialect, `additionalProperties: false`, complete `required`, version const 1 and absent remote capability properties.

- [x] **Step 2: Run RED, add schemas, run GREEN**

Run the contract suite before and after schemas; the first run must fail on missing files and the second pass.

- [x] **Step 3: Commit**

Commit: `feat(factory): publish closed M7 shadow schemas`.

### Task 4: Documentation and verification

**Files:** `README.md`, `DARK_FACTORY_ROADMAP.md`, `factory/README.md`, current change package tasks/ledger.

**Interfaces:** Exact product SHAs and fresh command outputs become current-state docs, not authority.

- [x] **Step 1: Update current graph/status without changing historical evidence**

Describe provisional M7 source, L2/human-merge ceiling and absent external surface; preserve all graph edges through M9.

- [x] **Step 2: Run provisional source verification**

Run the complete nested package suite from the repository root so package-qualified test imports remain valid: `UV_PROJECT_ENVIRONMENT=<external-venv> uv run --project factory --frozen python -m unittest discover -s factory/tests -t .`. Also run the focused repository structure/change-spec checks, schema/contract tests, Ruff and compilation.

- [ ] **Step 3: Run final dependency-restacked verification**

After factual M4 → M5 → M6 → M7 restack and final architecture ownership declaration, run `python3 scripts/grok_verify.py --mode pr` and every route-selected independent review. Do not issue a completion receipt before that tree exists.

- [x] **Step 4: Record exact provisional results and commit**

Use `git rev-parse HEAD`; append results to the ledger. Commit: `docs(m7): record provisional shadow handoff evidence`.
