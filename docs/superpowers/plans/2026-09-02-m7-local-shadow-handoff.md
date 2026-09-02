# M7 Local Shadow Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a closed immutable provider-independent local M7 shadow handoff and bounded cohort evaluator with no external-write surface.

**Architecture:** A pure contract module validates explicit M4/M5/M6 bridges and emits only a frozen `ready_for_human` bundle. A separate evaluator aggregates bounded non-PII outcomes for one exact trust tuple and returns stable failures or an L2 human-review recommendation. M4 runtime/store/service wiring stays absent.

**Tech Stack:** Python 3.11 frozen dataclasses, standard-library JSON/SHA-256, JSON Schema 2020-12, `unittest`, `uv --frozen`.

**Spec:** `docs/superpowers/specs/2026-09-02-m7-local-shadow-handoff-design.md`

## Global Constraints

- Exact local M4 base: `9fe779ab9f90719201acfd01160d3452658ff075`.
- M5 `161199bb163e0ba84ac1b32010be87f113df5e86` descends from local M4 but is not an accepted runtime dependency; M6 `5c5c37136f20404a927fd2ad7621ad0f7fcae8e6` remains provisional on older M5 bridge `61db79f07904ae5facb244c34b26c8383504dd88`.
- Output is only `ready_for_human`; maximum recommendation is `eligible_for_human_l2_review`.
- No service/API/store/migration, provider, network, credential, push, PR, merge, release or deploy surface.
- Hard deadline `2026-09-08 00:00 UTC+3` never waives a gate.
- Pure contract/evaluator source may proceed against opaque exact bridge values. Activation, completion and durable/runtime integration are **BLOCKED** until accepted M5 and M6 form factual M4 → M5 → M6 ancestry.
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

M5 `161199b…` and M6 `5c5c371…` both have merge-base M4 `9fe779…`, but their mutual merge-base is older M5 `61db79f…`. Latest M5 changed `execution_contracts.py` from the M6-carried blob `d9cb3c8…` to `e4237bf…` by closing the `WorkspaceResultV1` M4 disposition; M6 still exposes no task/run/fence/packet/result linkage. The planned M7 product files have no exact changed-path overlap with either branch, so use opaque exact bridges and keep activation blocked.

- [ ] **Step 2: Write failing tests**

Cover unknown versions/fields, accepted dependency states, task/run/fence/packet/head equality, pass-only complete semantic evidence, frozen values, digest mutation and forbidden push/URL/command/credential/auto-merge fields.

- [ ] **Step 3: Run RED**

Run: `cd factory && uv run --frozen python -m unittest tests.test_shadow_contracts -v`  
Expected: import failure for missing `adaptive_factory.shadow_contracts`.

- [ ] **Step 4: Implement minimal contracts and run GREEN**

Use closed constructors, bounded parsers, tuples, frozen dataclasses and domain-separated digests. Rerun the same command; expect all tests to pass.

- [ ] **Step 5: Commit**

Commit: `feat(factory): add immutable M7 shadow bundle contracts`.

### Task 2: Bounded outcome and evaluator

**Files:**
- Modify: `factory/src/adaptive_factory/shadow_contracts.py`
- Create: `factory/src/adaptive_factory/shadow_evaluation.py`
- Create: `factory/tests/test_shadow_evaluation.py`

**Interfaces:**
- Consumes: bundle/cohort digests and closed outcomes.
- Produces: `aggregate_shadow_cohort` and `evaluate_shadow_cohort`.

- [ ] **Step 1: Write failing aggregate tests**

Use 30 literal accepted fixtures with hand-derived counts/millionths, then mutate replay, tuple, sample, observation, baseline, quality, safety, budget/deadline and containment cases.

- [ ] **Step 2: Run RED**

Run: `cd factory && uv run --frozen python -m unittest tests.test_shadow_evaluation -v`  
Expected: missing evaluator import.

- [ ] **Step 3: Implement and run GREEN**

Reject empty/>10,000 cohorts, duplicate outcome/bundle identity and tuple mismatch; compute integer counts, exact millionths, nearest-rank p95 and median; sort failures; never emit promotion/merge actions. Run both M7 test modules.

- [ ] **Step 4: Commit**

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

- [ ] **Step 1: Add failing schema inventory/parity tests**

Assert exact file set, dialect, `additionalProperties: false`, complete `required`, version const 1 and absent remote capability properties.

- [ ] **Step 2: Run RED, add schemas, run GREEN**

Run the contract suite before and after schemas; the first run must fail on missing files and the second pass.

- [ ] **Step 3: Commit**

Commit: `feat(factory): publish closed M7 shadow schemas`.

### Task 4: Documentation and verification

**Files:** `README.md`, `DARK_FACTORY_ROADMAP.md`, `factory/README.md`, current change package tasks/ledger.

**Interfaces:** Exact product SHAs and fresh command outputs become current-state docs, not authority.

- [ ] **Step 1: Update current graph/status without changing historical evidence**

Describe provisional M7 source, L2/human-merge ceiling and absent external surface; preserve all graph edges through M9.

- [ ] **Step 2: Run verification**

Run `cd factory && uv run --frozen python -m unittest discover -s tests -v`, then `python3 scripts/grok_verify.py --mode pr`.

- [ ] **Step 3: Record exact results and commit**

Use `git rev-parse HEAD`; append results to the ledger. Commit: `docs(m7): record provisional shadow handoff evidence`.
