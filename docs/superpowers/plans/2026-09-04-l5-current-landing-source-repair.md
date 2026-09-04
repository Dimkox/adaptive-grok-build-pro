# L5 Current Landing Source Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make offline L5 accept exact landing commit `699010380f4f90a0193a9c22090c35e6aded7d2c` and seal its complete 20-member site artifact without widening write or operational authority.

**Architecture:** Rotate the exact source epoch across renderer and OpenAPI, treat `/index.css` as immutable source surface, and add it to the closed deploy inventory. Candidate generation remains a deterministic two-file delta in a private no-local clone; provider and publisher defaults remain unavailable.

**Tech Stack:** Python 3.11+, stdlib `unittest`, Git plumbing, FastAPI TestClient, OpenAPI 3.1 JSON.

**Spec:** `engineering/changes/20260904-repair-l5-current-landing-source-binding-eb3f80/change-spec.yaml`

## Global Constraints

- Exact target: `github.com/Dimkox/ai-dark-factory-landing` commit `699010380f4f90a0193a9c22090c35e6aded7d2c`, tree `f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4`.
- `LANDING_WRITE_PATHS` remains exactly `index.html` and `content.css`.
- `index.css` is protected source provenance and the deploy inventory is exactly 20 members.
- Published `v2.0.14` ZIP/sidecar and historical L5 evidence are immutable.
- No provider call, package rebuild, target mutation, deployment, or external write.
- One focused red-green cycle, one full PR verifier, and one selected review wave.

---

### Task 1: Prove the Current-Source Regression

**Files:**
- Modify: `factory/tests/test_landing_renderer.py`
- Modify: `factory/tests/test_landing_artifact.py`
- Modify: `factory/tests/test_landing_contracts.py`
- Modify: `factory/tests/test_landing_api.py`
- Modify: `factory/tests/test_landing_intake.py`
- Modify: `factory/tests/test_landing_provider.py`

**Interfaces:**
- Consumes: current `source_surface_facts`, `ExactGitLandingWorkspace`, `DEPLOY_MEMBERS`, and OpenAPI exact-base parameters.
- Produces: failing behavior tests for an external `/index.css`, exact 20-member source provenance, and new pin/API cutover.

- [x] **Step 1: Change the hermetic source fixture to the accepted topology**

Remove its inline `<style>`, add exact `<link rel="stylesheet" href="/index.css">`, add a regular `index.css` fixture, and keep generated writes asserted as `{"index.html", "content.css"}`.

- [x] **Step 2: Add independent behavior assertions**

Assert the rendered page has one `/index.css` and one `/content.css`; unknown/duplicate/inline style surfaces fail; the candidate preserves `index.css` mode/object; the ZIP has 20 members and its `index.css` record is source provenance with equal object IDs and bytes.

- [x] **Step 3: Update expected current identity in contract/intake/provider/API fixtures**

Use the exact target values from Global Constraints, expect OpenAPI `1.0.1`, and make the fake artifact count 20. Add stale/mixed tuple assertions that return `409 source_identity` without a provider call.

- [x] **Step 4: Run the smallest tests and observe RED**

Run resolved test methods in `test_landing_renderer`, `test_landing_artifact`, and `test_landing_contracts`. Expected failures must specifically show `source_active_content`, missing `index.css`/19-member inventory, or stale OpenAPI/source constants; loader or fixture errors are not evidence.

### Task 2: Repair Renderer Source Epoch and Surface

**Files:**
- Modify: `factory/src/adaptive_factory/landing_renderer.py`
- Test: `factory/tests/test_landing_renderer.py`

**Interfaces:**
- Consumes: the exact target and RED tests from Task 1.
- Produces: `TARGET_BASE_SHA`, `TARGET_BASE_TREE`, and `RENDERER_VERSION = "1.0.1"`; `source_surface_facts(str) -> LandingSourceSurfaceFacts` that binds `/index.css` and permits only the renderer's fixed optional `/content.css`.

- [x] **Step 1: Rotate the exact source constants atomically**

Set SHA/tree to Global Constraints and bump renderer identity to `1.0.1`; do not change repository ID, default branch, clone, checkout, `git add`, or write allowlist.

- [x] **Step 2: Replace the obsolete inline-style fact**

Reject any inline `<style>`. Require one exact `<link rel="stylesheet" href="/index.css">`; allow zero or one exact `<link rel="stylesheet" href="/content.css">`; reject any other or duplicate stylesheet-loading tag. Digest only the protected raw `index.css` tag in `LandingSourceSurfaceFacts` so source/candidate facts remain comparable.

- [x] **Step 3: Run renderer tests and observe GREEN**

Run `PYTHONPATH=.:factory/src python3 -m unittest factory.tests.test_landing_renderer -v`. Expected: all methods pass and the candidate delta remains exactly two files.

### Task 3: Complete Artifact and API Contract

**Files:**
- Modify: `factory/src/adaptive_factory/landing_artifact.py`
- Modify: `factory/contracts/openapi/landing-dogfood.v1.json`
- Test: `factory/tests/test_landing_artifact.py`
- Test: `factory/tests/test_landing_contracts.py`
- Test: `factory/tests/test_landing_api.py`

**Interfaces:**
- Consumes: Task 2 exact candidate and protected `index.css` tree member.
- Produces: sorted 20-member artifact and OpenAPI metadata version `1.0.1` advertising the same SHA/tree.

- [x] **Step 1: Add only `index.css` to `DEPLOY_MEMBERS`**

Do not add it to `LANDING_WRITE_PATHS`; retain all existing regular-file, mode, object, deterministic ZIP, and no-replace validation.

- [x] **Step 2: Update the OpenAPI patch contract**

Set `info.version` to `1.0.1` and exact header constants to Global Constraints. Keep paths, operations, media types, responses, and referenced JSON schemas unchanged.

- [x] **Step 3: Run the focused landing modules**

Run `PYTHONPATH=.:factory/src python3 -m unittest factory.tests.test_landing_renderer factory.tests.test_landing_artifact factory.tests.test_landing_contracts factory.tests.test_landing_api factory.tests.test_landing_intake factory.tests.test_landing_provider -v`. Expected: all pass with no provider, publisher, target, or network effect.

### Task 4: Freeze the Unreleased Handoff

**Files:**
- Modify: `README.md`
- Modify: `factory/README.md`
- Modify: `START_HERE.md`
- Modify: `PROJECT_STATE.json`
- Modify: `CHANGELOG.md`
- Modify: `decisions.md`
- Modify: `mistakes.md`
- Modify: `engineering/changes/20260904-repair-l5-current-landing-source-binding-eb3f80/*.md`

**Interfaces:**
- Consumes: green exact source/artifact behavior from Task 3.
- Produces: a fresh-clone handoff that distinguishes the unreleased repair from immutable published `v2.0.14` and names task 2 of the five-step operationalization sequence.

- [x] **Step 1: Record current versus historical truth**

Document the new exact source and 20-member current behavior without rewriting the historical 19-member `v2.0.14` release facts or old L5 change package.

- [x] **Step 2: Record self-learning facts**

In `mistakes.md`, record the avoidable `rm -f` denial root cause and the route classifier's substring matches (`d7` inside the SHA and `rag` inside `coverage`). In `decisions.md`, record that exact source assets remain source-owned and that historical release evidence is not rewritten during a forward repair.

- [x] **Step 3: Run focused static and documentation checks**

Run targeted Ruff/Bandit for modified Python files, JSON parsing for changed JSON, `git diff --check`, and affected structure/state tests. Fix only actual failures in changed behavior.

### Task 5: Commit and Hand Off to the Single Final Gate

**Files:**
- Modify: no additional product files.

**Interfaces:**
- Consumes: all green focused checks and completed tracked handoff.
- Produces: one clean commit ready for the controller's single full verifier and one three-review wave.

- [x] **Step 1: Inspect the complete diff and immutable files**

Confirm no package ZIP/sidecar, migration, old L5 package, target repository, provider, publisher, or external resource changed.

- [x] **Step 2: Commit the frozen repair**

Stage only the planned tracked files and commit with message `fix: bind L5 to current landing source`. Report commit SHA, tree, focused commands/results, and changed paths to the controller.

- [x] **Step 3: Stop broad validation**

Do not run `grok_verify` or dispatch reviewers from the implementer. The controller owns exactly one full verifier and the route-selected `code_reviewer`, `test_reviewer`, and `security_reviewer` wave on the frozen commit.
