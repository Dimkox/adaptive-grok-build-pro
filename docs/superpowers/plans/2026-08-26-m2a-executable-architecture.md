# M2-A Executable Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development`. Repository routing overrides the skill's fresh-writer pattern: the single route-selected `data_implementer` owns every application-code task; route-selected read-only reviewers provide the independent gates.

**Goal:** Publish a strict, deterministic architecture contract and local fitness/evidence engine for the current stack without mutating `trust-ci/**` or implementing later factory runtime milestones.

**Architecture:** Two canonical JSON-compatible YAML documents describe current components and rules. Dependency-free Python modules load and validate them, compute stable digests/diffs/fitness/risk, render deterministic Mermaid projections, and bind results into local verification and receipts. M2-B independently enforces the frozen contract in a separate factory task.

**Tech Stack:** Python 3.11+/stdlib, Draft 2020-12 schema documents using the existing supported subset, AST/static data analysis, unittest, Git object reads, existing Adaptive Grok verification and receipt interfaces.

**Spec:** `docs/superpowers/specs/2026-08-26-m2-executable-architecture-design.md`

## Global Constraints

- M2 adoption base is exactly `25bfbe59ea188d9687b20a9caad19e7db3d031f8`; preserve the historical route base separately.
- Exactly one application-code writer: route-selected `data_implementer` for all tasks.
- Do not modify any path under `trust-ci/**` in M2-A.
- No GitHub Actions, root packaging marker, dependency, PyYAML/jsonschema, service, database, migration, queue, framework, provider adapter, systemd unit, external integration, or external write.
- `change-spec.yaml` remains intent authority; architecture system/rules remain architecture authority; diagrams and K16 are non-authoritative projections.
- New architecture documents are canonical strict JSON text; no legacy YAML decoder and no unknown future version fallback.
- Unsupported applicable language, contract, SQL, or rule semantics fail closed; they never become `pass` or silent `not_applicable`.
- Risk is monotonic and architecture-significant changes revoke docs exemptions.
- Consumer models are target-owned: installation may provide code/schema/template but never create or overwrite adopted `architecture/system.yaml` or `architecture/rules.yaml`.
- Every behavior task follows RED, GREEN, focused verification, self-review, commit, independent task review.

---

### Task 1: Strict architecture schemas, canonical loader, models, and digests

**Files:**
- Create: `schemas/architecture-system.schema.json`
- Create: `schemas/architecture-rules.schema.json`
- Create: `.grok-stack/adaptive_grok/architecture.py`
- Modify only if needed for safe reuse: `.grok-stack/adaptive_grok/spec.py`
- Test: `tests/test_architecture_model.py`

**Interfaces:**
- `ArchitectureError(ValueError)`
- `load_architecture(root, system_path=None, rules_path=None) -> ArchitectureSnapshot`
- `validate_architecture(snapshot, root) -> tuple[ArchitectureFinding, ...]`
- `architecture_digests(snapshot) -> dict[str, str]`
- `architecture_fingerprint(root, snapshot, *, base_sha, head_sha, contract_digests) -> str`
- Bounded constants: documents <= 1,000,000 bytes each, depth <= 64, total parsed nodes <= 100,000, model nodes <= 128, edges <= 512, rules <= 256.

- [ ] Add failing tests for valid minimal documents, exact required fields, unknown keys/version, duplicate JSON keys/IDs, unresolved references, duplicate capability edges, unsafe/absolute/backslash/control paths, symlink/non-regular files, surrogates, excessive bytes/depth/counts, canonical order normalization, digest stability, and semantic-edit digest changes.
- [ ] Run `python3 -m unittest tests.test_architecture_model -v` and capture expected RED evidence.
- [ ] Add two strict schemas with closed objects and only schema keywords supported by the repository validator.
- [ ] Implement safe reads, strict JSON parsing, schema/semantic validation, normalization, component/composite digests, and adoption-aware fingerprints. If generic M1 parsing is safely promoted, retain all M1 behavior and characterization tests.
- [ ] Keep `failure_behavior` once per edge with `mode`, `timeout_ms`, `max_retries`, `idempotency`, `correlation_id`, `terminal_action`, and `observable_signal`; accept only `direction=from_to` in v1.
- [ ] Run focused tests and `python3 -m unittest tests.test_change_spec -v`; both must pass.
- [ ] Commit: `feat: add strict architecture contract`

---

### Task 2: Seed current architecture, contract baselines, and drift validation

**Files:**
- Create: `architecture/system.yaml`
- Create: `architecture/rules.yaml`
- Create: `engineering/contracts/openapi/trust-ci.v1.json`
- Create: `engineering/contracts/schemas/trust-ci-approval-envelope.v1.json`
- Create: `engineering/contracts/schemas/trust-ci-attestation-envelope.v1.json`
- Create: `engineering/contracts/schemas/github-pull-request-projection.v1.json`
- Modify: `.grok-stack/adaptive_grok/architecture.py`
- Test: `tests/test_architecture_model.py`
- Test fixtures: `tests/fixtures/architecture/**` only when a focused fixture is clearer than an inline document.

**Interfaces:**
- `validate_repository_drift(root, snapshot) -> tuple[ArchitectureFinding, ...]`
- `contract_inventory(root, snapshot) -> tuple[ContractRecord, ...]`
- `compare_contracts(base, head, policy) -> CompatibilityResult`

- [ ] Add failing tests for missing/escaping/symlinked repository paths and contracts, undeclared source/API drift, additive compatible change, removed operation/event/property, new required input, narrowed enum/type, widened producer output, weakened authentication, unsupported schema keywords, same-version semantic change, and deterministic inventory digest.
- [ ] Run focused tests and capture RED.
- [ ] Seed only current components and directed capabilities: local route/policy, change/spec/evidence, verifier, Trust CI API/PostgreSQL/worker/workspace/Docker/runner/external holdout, GitHub/App publication, and human approval. Label source-described versus externally operated facts honestly; record Docker TCP/2375 as existing `authentication=none`, constrained, and non-expandable.
- [ ] Add bounded machine-readable baselines for existing Trust CI endpoints and envelope/projection shapes without changing runtime behavior or claiming full GitHub payload ownership.
- [ ] Implement contained path/contract inventory and conservative directional compatibility for the documented JSON/OpenAPI subset. Unknown applicable semantics return `unsupported`.
- [ ] Ensure examples and `.gitkeep` files never become declared contracts.
- [ ] Run `python3 -m unittest tests.test_architecture_model -v` and existing contract/spec tests.
- [ ] Commit: `feat: model current architecture and contracts`

---

### Task 3: Exact architecture diff, mandatory fitness, and monotonic risk

**Files:**
- Create: `.grok-stack/adaptive_grok/architecture_fitness.py`
- Modify: `.grok-stack/adaptive_grok/architecture.py`
- Create: `tests/test_architecture_fitness.py`

**Interfaces:**
- `diff_architecture(root, *, base_sha, head_sha=None, worktree=False) -> ArchitectureDiff`
- `evaluate_fitness(root, snapshot, diff, changed_paths, *, pre_risk) -> FitnessReport`
- `architecture_evidence(root, *, base_sha, head_sha, pre_risk) -> dict[str, Any]`
- Results: `pass|fail|not_applicable|unsupported`; risk: `green<yellow<red`, `post=max(pre, escalation)`.

- [ ] Add failing table-driven tests for adoption bootstrap, clean exact base/head requirements, NUL-safe odd paths, deterministic change records/diff digest, and every mandatory category: forbidden edge; module boundary; public API/event/schema compatibility; migration expand/migrate/contract and mirrored history; tenant/auth; undeclared network client; production import from tests/governance; product plus `trust-ci/**` mixing; changed-code bytes/lines/AST complexity; background-job idempotency/correlation/observable failure/bounded retries/dead-letter; secret trusted-edge flow; runner/factory trust-material isolation.
- [ ] Test that every category emits a result, `not_applicable` includes predicate/scanned scope/reason/inventory digest, unsupported applicable analysis fails, new architecture triggers revoke non-applicability/docs exemption, and pre-risk never decreases.
- [ ] Run `python3 -m unittest tests.test_architecture_fitness -v` and capture RED.
- [ ] Implement exact Git object reads and `git diff --name-only -z --no-renames`, adoption-only absent base, sorted typed diff records, applicability evidence, bounded Python AST/source/SQL/contract analyzers, and monotonic risk/approval triggers.
- [ ] Enforce the M2-A slice itself contains no `trust-ci/**` changes relative to the frozen adoption base.
- [ ] Keep fitness code below its own module budgets by using focused functions; do not exempt M2 implementation from declared budgets.
- [ ] Run both architecture test modules and existing SQL/verification tests.
- [ ] Commit: `feat: enforce architecture fitness and risk`

---

### Task 4: Deterministic CLI, diagrams, verification, receipts, and staleness

**Files:**
- Create: `.grok-stack/adaptive_grok/architecture_diagrams.py`
- Create: `scripts/grok_architecture.py`
- Create: `architecture/generated/context.mmd`
- Create: `architecture/generated/container.mmd`
- Create: `architecture/generated/deployment.mmd`
- Create: `architecture/generated/data-flow.mmd`
- Create: `architecture/generated/trust-boundary.mmd`
- Modify: `.grok-stack/adaptive_grok/verification.py`
- Modify: `.grok-stack/adaptive_grok/receipts.py`
- Test: `tests/test_architecture_model.py`
- Test: `tests/test_architecture_fitness.py`
- Test: `tests/test_change_receipts.py`
- Test: `tests/test_verification_doctor.py`

**Interfaces:**
- CLI subcommands: `validate`, `summary`, `diagram`, `diff`, `fitness`, `drift`; all support deterministic `--json` where meaningful.
- `diagram --check` performs byte comparison without a renderer.
- Verification report key `architecture` contains schema/system/rules/architecture/evidence digests, base/head kind, drift/fitness status, risk, and generated artifact digests.
- Receipts bind `architecture_digest` and `architecture_fingerprint` after adoption.

- [ ] Add failing CLI tests for stable JSON, non-zero invalid status, explicit root/base/head, dirty-worktree labelling, bootstrap diff, and byte-for-byte diagram check.
- [ ] Add failing verification/receipt tests for architecture metadata, missing adopted model, architecture/contract/base/head staleness, preserved M1 spec criteria, and unconfigured consumer compatibility.
- [ ] Run focused test modules and capture RED.
- [ ] Implement five sorted Mermaid projections with deterministic escaping/LF/no timestamps and a check-only mode.
- [ ] Implement CLI without mutable runtime-state dependency for explicit inputs and without writing outside explicit diagram generation.
- [ ] Add the architecture check beside M1 spec checks; preserve docs-exemption restrictions and do not claim local evidence is merge authority.
- [ ] Extend receipts backward-compatibly: legacy receipts remain readable, but cannot satisfy an adopted M2 route without current architecture binding.
- [ ] Run focused tests, then `python3 -m unittest discover -s tests`.
- [ ] Commit: `feat: bind architecture evidence to verification`

---

### Task 5: Installer delivery, durable package, docs, and M2-A verification

**Files:**
- Modify: `scripts/install_into.py`
- Modify: `.grok-stack/adaptive_grok/manifest.py` and packaging lists only where existing delivery requires it
- Create: `.grok-stack/templates/architecture/system.example.yaml`
- Create: `.grok-stack/templates/architecture/rules.example.yaml`
- Modify: `tests/test_installer.py`
- Modify: `tests/test_manifest_package.py`
- Modify: `tests/test_structure.py`
- Modify: `README.md`
- Modify: `QUICKSTART.md`
- Modify: `DARK_FACTORY_ROADMAP.md` only for source-backed M2-A items
- Modify: `decisions.md` for durable rulings that proved useful
- Complete: `engineering/changes/20260826-m2-executable-architecture-015603/**`

**Interfaces:**
- Installer delivers modules/CLI/schemas/template but never target-owned `architecture/system.yaml` or `architecture/rules.yaml`.
- README calls K16 a decorative inventory and links the actual architecture authority/CLI/generated views.
- M2-A typed spec is red-risk, placeholder-free, gate-valid, criterion-mapped, and explicitly defers M2-B/deployment evidence.

- [ ] Add failing installer/package/structure tests for managed architecture code/schema/template, no target model overwrite under normal or `--force`, K16 decorative-only wording while preserving all 120 edges, and required architecture files/links.
- [ ] Run focused tests and capture RED.
- [ ] Implement installer/manifest changes without copying target models or `trust-ci/**` material.
- [ ] Complete the durable package with frozen M1 adoption base, acceptance criteria, invariants, forbidden outcomes, architecture approval scope, risk/test/rollback/release evidence, and the M2-B dependency. Record that no migration/external write occurred.
- [ ] Update docs and only check roadmap items proven by exact source evidence. Do not mark independent/deployed holdout exit criteria complete.
- [ ] Run `python3 scripts/grok_spec.py validate --change-id 20260826-m2-executable-architecture-015603 --gate --json`.
- [ ] Run `python3 -m unittest discover -s tests`, `python3 -m compileall -q .grok-stack/adaptive_grok scripts`, `python3 scripts/grok_architecture.py diagram --check`, and `python3 scripts/grok_verify.py --mode pr --no-record --json`.
- [ ] Confirm `git diff --name-only 25bfbe59ea188d9687b20a9caad19e7db3d031f8...HEAD -- trust-ci` is empty.
- [ ] Commit: `docs: complete M2-A executable architecture evidence`

After Task 5, transition the package through verification/review, dispatch all route-selected reviewers against the exact final M2-A diff, fix any load-bearing findings through the same writer, transition to `ready`, then record fresh fingerprint-bound receipts after the final repository write. Do not push or open a PR without explicit authorization. Start M2-B only in a separate worktree/branch/route/package from the frozen M2-A contract head.

---

### Task 6: Approved read-only projection and package-aware provenance pivot

**Files:**
- Modify: `.grok-stack/adaptive_grok/architecture_diagrams.py`
- Modify: `.grok-stack/adaptive_grok/architecture_fitness.py`
- Modify: `scripts/grok_architecture.py`
- Modify: `tests/test_architecture_model.py`
- Modify: `tests/test_architecture_fitness.py`
- Modify: `README.md`, `QUICKSTART.md`, and the active change package only where their operator contract changes

**Interfaces:**
- `render_diagrams(snapshot) -> dict[str, str]` remains deterministic and bounded.
- `compare_generated(root, rendered) -> tuple[str, ...]` remains no-follow and read-only.
- Remove the public `write_generated` capability and all publication/cleanup helpers that exist only for repository mutation.
- `diagram` without `--check` returns `artifacts`, `digests`, `checked=false`, and `ok=true`; `diagram --check` returns digests and mismatches without artifacts or writes.
- Queue analysis returns one structured state (`resolved`, `not_queue`, or `unsupported`) plus stable reason and signals; both background-job fitness and `new_queue` risk consume it.
- Relative imports resolve from the containing package: for `project/jobs/__init__.py`, `from .celery_app import app` resolves `project.jobs.celery_app`; for `project/jobs/worker.py`, the same level resolves from `project.jobs`.

- [ ] **Step 1: write diagram RED tests.** Replace mutation-race tests with behavior tests proving that invoking `diagram` without `--check` returns all five literal Mermaid artifacts while a monkeypatched `os.open`, `os.rename`, `os.unlink`, `os.rmdir`, `os.mkdir`, `os.chmod`, and `os.replace` mutation boundary is never reached; assert repository bytes and inventory are unchanged.
- [ ] **Step 2: verify diagram RED.** Run `python3 -m unittest -v tests.test_architecture_model.ArchitectureModelTests.test_diagram_render_is_repository_read_only tests.test_architecture_fitness.ArchitectureFitnessTests.test_architecture_cli_exact_diff_and_diagram_check`; expect failure because the current CLI calls `write_generated` and omits rendered artifacts.
- [ ] **Step 3: implement the minimal read-only diagram API.** Remove `write_generated` and publication/cleanup code; make the CLI return `{ "artifacts": rendered, "checked": false, "digests": artifact_digests(rendered), "mismatches": [], "ok": true }` for render and preserve no-follow comparison for check.
- [ ] **Step 4: verify diagram GREEN.** Rerun the two focused tests and confirm both pass with an unchanged repository inventory.
- [ ] **Step 5: write queue RED tests.** Add literal base/head fixtures for `project/jobs/__init__.py -> from .celery_app import app`, `project/jobs/worker.py -> from .celery_app import app`, multi-hop re-exports, a boundary-exceeding relevant chain, an unresolved queue-adjacent local adapter, and unrelated local `submit`, `delay`, and `task` methods. Assert positive and unsupported cases fail fitness with `new_queue`; unrelated cases remain `not_applicable` with no trigger.
- [ ] **Step 6: verify queue RED.** Run the new selectors with `python3 -m unittest -v`; expect the package-`__init__` cases to fail as `not_applicable` under the current module resolver.
- [ ] **Step 7: implement the minimal package-aware fail-closed resolver.** Distinguish module files from package initializers when calculating the import package, return an explicit provenance result with stable reason, propagate resolver ceilings and relevant unresolved imports as `unsupported`, and delete terminal-name fallbacks.
- [ ] **Step 8: verify queue GREEN and shared signaling.** Run all queue provenance tests and assert background fitness status and `new_queue` are derived from the same result for every table row.
- [ ] **Step 9: update operator documentation and durable evidence.** State that diagram generation is stdout-only/read-only, checked-in projection changes use normal reviewed edits, and no queue/runtime capability was added. Record the approved pivot and rollback as reverting this source-only commit.
- [ ] **Step 10: run final checks.** Run both architecture test modules, full unittest discovery, Ruff, Bandit, compileall, spec gate, architecture validate/drift/diagram-check, exact `trust-ci/**` separation, and `python3 scripts/grok_verify.py --mode pr --no-record --json`.
- [ ] **Step 11: commit.** Commit the coherent pivot as `refactor: make architecture evidence read-only` and attach RED/GREEN/full-command evidence under the active change package.
