# Workflow Artifact Adapters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a safe model-neutral workflow artifact compiler and convergence gate for GitHub Spec Kit, BMAD, and Superpowers projections.

**Architecture:** A descriptor-bound loader feeds closed adapters into immutable canonical JSON contracts. A route-bound compiler creates a stable task DAG and deterministic convergence report, while the verifier treats the feature as opt-in and read-only.

**Tech Stack:** Python standard library, JSON Schema draft 2020-12 subset, unittest, existing Adaptive Grok verifier and installer.

**Spec:** `docs/superpowers/specs/2026-08-30-workflow-artifact-adapters-design.md`

## Global Constraints

- Imported content is untrusted advisory data and cannot create authority, receipts, approvals, roles, gates, or merge eligibility.
- No network, subprocess, shell, LLM, fuzzy inference, external dependency, database, or GitHub Actions.
- Writes are explicit serialized CAS publications limited to exact derived `task-graph.json` / `convergence-report.json` targets and marked active-change workflow projections/exports.
- Historical change packages without a workflow manifest remain compatible.

---

### Task 1: Safe source contracts and loader

**Files:** Create `schemas/workflow-source-v1.schema.json`, `.grok-stack/adaptive_grok/workflow_artifacts.py`; test `tests/test_workflow_artifacts.py`.

**Interfaces:** Produce `load_source_manifest(root, manifest_path) -> SourceBundle`, `canonical_json(value) -> bytes`, and typed `WorkflowArtifactError`.

- [ ] Add tests that valid explicit manifests normalize deterministically and path escape, symlink, FIFO, duplicate key/path, non-NFC, YAML authority syntax, replacement, and size/depth/node limits fail with typed errors.
- [ ] Run `python3 -m unittest tests.test_workflow_artifacts.WorkflowSourceTests` and confirm feature-missing failures.
- [ ] Implement descriptor-relative no-follow bounded reads, strict JSON, source role allowlists, NFC checks, and canonical digests.
- [ ] Rerun the focused class and require PASS.

### Task 2: Adapters and canonical task graph

**Files:** Create `schemas/workflow-task-graph-v1.schema.json`; modify `.grok-stack/adaptive_grok/workflow_artifacts.py`; test `tests/test_workflow_artifacts.py`.

**Interfaces:** Produce `compile_task_graph(root, change_id, bundle, route) -> dict` with stable task IDs and explicit route ownership.

- [ ] Add failing tests for Spec Kit, BMAD, and Superpowers mappings; excluded personas/orchestration; stable IDs; missing dependencies; cycles; write conflicts; shell strings; and uncovered AC/INV/FORBID IDs.
- [ ] Run the adapter/graph tests and confirm expected failures.
- [ ] Implement closed role mappings, bounded native Spec Kit/BMAD task and status parsing, optional exact `AGB:` overrides, explicit enrichment findings, stable DAG compilation, route writer/reviewer binding, tightly allowlisted non-executed RED/GREEN verification argv, interface/file declarations, and coverage validation.
- [ ] Rerun adapter/graph tests and require PASS.

### Task 3: Deterministic convergence

**Files:** Create `schemas/workflow-convergence-report-v1.schema.json`; modify `.grok-stack/adaptive_grok/workflow_artifacts.py`; test `tests/test_workflow_artifacts.py`.

**Interfaces:** Produce `converge(root, change_id, bundle, graph, route) -> dict` and `validate_stored_workflow(root, change_id, route) -> tuple[dict, dict]`.

- [ ] Add failing tests for source digest drift, goal/AC conflict, placeholders, architecture contradiction, incomplete coverage, source-status drift, receipt-derived effective-status transition without tracked edits, deterministic findings, and explicit dispositions.
- [ ] Run convergence tests and confirm expected failures.
- [ ] Implement deterministic finding IDs/order, blocking dispositions, ordinary Markdown checkbox source-status mapping, ephemeral effective status from orchestration-supplied fingerprint plus canonical receipt checks, and shared stored/produced graph/report validation without persisting fingerprints.
- [ ] Rerun convergence tests and require PASS.

### Task 4: CLI and bounded projections

**Files:** Create `scripts/grok_artifacts.py`; modify `.grok-stack/adaptive_grok/workflow_artifacts.py`; test `tests/test_workflow_artifacts_cli.py`.

**Interfaces:** Commands `import`, `compile`, `converge`, `validate`, `export`; all emit JSON, default read-only; `--write --expected-digest <sha256>` enables bounded CAS publication.

- [ ] Add failing CLI tests for read-only default, descriptor-safe closed active route/change reads, active-change containment, non-authoritative export banners, source-tree immutability, CAS creation/update/mismatch/special-entry/double-race recovery, and non-zero blocking validation.
- [ ] Run `python3 -m unittest tests.test_workflow_artifacts_cli` and confirm failures.
- [ ] Implement the five commands and per-target serialized CAS publication for exact `workflow/task-graph.json`, `workflow/convergence-report.json`, and marked files beneath `workflow/projections` or `workflow/exports`; rollback before inspecting displaced content, preserve every unowned competitor and recovery entry, and fail closed where atomic exchange is unavailable.
- [ ] Rerun CLI tests and require PASS.

### Task 5: Verifier, distribution, and documentation

**Files:** Modify `.grok-stack/adaptive_grok/verification.py`, `scripts/install_into.py`, `tests/test_verification_doctor.py`, `tests/test_installer.py`, `tests/test_manifest_package.py`, `README.md`, `QUICKSTART.md`, `PROJECT_STATE.json`, change-package documents, and `decisions.md`.

**Interfaces:** Add opt-in `workflow-artifacts` verifier result after spec/architecture/governance; absent manifests return `skip`.

- [ ] Add failing integration tests proving stored graph/report are checked read-only, stale artifacts fail, historical packages skip, and packaging/installer include all new files without source mutation.
- [ ] Run the focused verification/installer/package tests and confirm failures.
- [ ] Wire the read-only check, inventory, docs, observability, release/rollback notes, and complete task statuses.
- [ ] Run focused tests, full `python3 -m unittest discover -s tests -v`, then `python3 scripts/grok_verify.py --mode pr`.
- [ ] Request route-selected independent code, test, security, and release reviews against the same final fingerprint; record receipts only after the final repository mutation.
