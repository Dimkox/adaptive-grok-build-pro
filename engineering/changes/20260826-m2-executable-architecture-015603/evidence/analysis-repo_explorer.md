# M2 repository exploration

## Scope and baseline

- Worktree: `/home/pall/grok-projects/adaptive-grok-build-pro-m2`; HEAD `25bfbe5` (`docs: record holdout verification race`), based on route base `069fe82`.
- Active route `0156034c05bd` is architecture/high-risk with API, data, event, and security domains. It selects `data_implementer` as the sole writer, six analysis agents, and code/test/security/data/release reviews. The active M2 package is still a placeholder package; its `change-spec.yaml` is generated v2 JSON with no criteria and `UNKNOWN` objective metric/target, so Task 6-style package completion is still required for M2.
- The required M2 source is `DARK_FACTORY_ROADMAP.md:354-443`. The approved overall design is `/home/pall/grok-projects/adaptive-grok-build-pro-agent-factory/docs/superpowers/specs/2026-08-26-model-agnostic-autonomous-factory-design.md`; its relevant contract is that M2/M3 publish stable versioned intent-plane contracts consumed later by M4, while M4+ must not invent replacements.

## Current architecture-related tree

No M2 implementation files exist yet:

- absent: `architecture/system.yaml`, `architecture/rules.yaml`, `schemas/architecture.schema.json`, `.grok-stack/adaptive_grok/architecture.py`, `scripts/grok_architecture.py`, `tests/test_architecture_model.py`, `tests/test_architecture_fitness.py`, `trust-ci/holdout.example/architecture_validate.py`;
- no `architecture/`, `governance/`, or `factory/` product roots exist;
- `README.md` contains a complete pairwise Mermaid inventory graph of local Grok and Trust CI nodes, and `tests/test_structure.py` enforces that graph. The roadmap explicitly says this K16-style graph remains decorative and cannot be architecture evidence.

The only current contract examples are `examples/contracts/openapi/example.yaml`, `examples/contracts/asyncapi/example.yaml`, and `examples/contracts/schemas/order-changed.v1.json`. Existing local contract checks are `_contracts()` in `.grok-stack/adaptive_grok/verification.py`; repository detection recognizes `engineering/contracts/openapi`, `engineering/contracts/asyncapi`, root OpenAPI/AsyncAPI files, and data directories in `.grok-stack/adaptive_grok/repo.py`.

## Reusable local interfaces

- `.grok-stack/adaptive_grok/util.py` provides `find_root`, bounded subprocess `run`, `git_output`, `git_head`, `changed_files(root, base)`, `file_sha256`, `tree_fingerprint`, `safe_relative_path`, and bounded text reads. `changed_files()` merges base diff, staged, unstaged, and untracked paths; architecture diff/risk checks should reuse it and sort all output deterministically.
- `.grok-stack/adaptive_grok/spec.py` is the completed M1 model. Current v2 interfaces include `load_spec(path, allow_legacy=...)`, `validate_spec(root, path, gate=..., route=...)`, `canonical_spec_digest`, `criterion_coverage`, and `spec_fingerprint`. `spec_fingerprint` already binds canonical spec digest, route `base_commit`, current Git HEAD, and declared contract file digests. It intentionally has no architecture digest field; M2 should expose a parallel architecture digest/fingerprint rather than mutate M1 intent semantics.
- `.grok-stack/adaptive_grok/verification.py` has `CheckResult`, `_command_check`, `_contracts`, `_sql_safety`, `_change_specs`, and `verify()`. `_change_specs` is the closest integration pattern: collect changed/active files, perform draft/gate validation, return a check plus structured metadata, and include metadata under a report key. M2 can add an independent architecture check alongside it without making architecture validation depend on untrusted application code.
- `.grok-stack/adaptive_grok/receipts.py` already binds receipts to route, tree fingerprint, active spec digest/fingerprint, and criterion IDs. M2 architecture evidence should either extend the same binding with architecture digest or record an architecture evidence envelope with exact tree/head/base bindings; it must not weaken current spec staleness checks.
- `.grok-stack/adaptive_grok/change.py` and `.grok-stack/templates/change/` generate durable packages. M2 should keep package generation and architecture model validation separate: a model/rules digest belongs in future durable packet inputs, not in mutable Markdown.
- `.grok-stack/adaptive_grok/state.py` offers runtime locks, active route/change, agent lifecycle, and exact delegated grants. It is local advisory state only; it cannot become M2 merge authority.

## M1 compatibility baseline

M1 was completed in commits `df30427` through `25bfbe5`, including:

- v2 schema plus v1 compatibility schema: `schemas/change-spec.schema.json`, `schemas/change-spec-v1.schema.json`;
- bounded canonical JSON parser/legacy reader and path-safe contract/evidence validation in `.grok-stack/adaptive_grok/spec.py`;
- `scripts/grok_spec.py` commands `validate`, `summary`/`summarize`, `coverage`, `map`, and `generate`;
- route generation and typed-authority notices in `.grok-stack/adaptive_grok/change.py` and change templates;
- criterion/spec-bound receipts and verification report `spec` metadata;
- independent `trust-ci/holdout.example/change_spec_validate.py` with exact-SHA changed-spec selection;
- backward-compatible `AttestationPayload.spec_digest` and `criterion_coverage`, plus trusted data-only extraction in `trust-ci/src/adaptive_trust_ci/runner.py`.

M1 tests currently cover the path-safe/untrusted-input boundary (`tests/test_change_spec.py`, `tests/test_change_receipts.py`, `tests/test_verification_doctor.py`, `trust-ci/tests/test_change_spec_holdout.py`, `trust-ci/tests/test_runner.py`). The focused command `python3 -m unittest tests.test_change_spec tests.test_change_receipts tests.test_verification_doctor -q` passed 74 tests at this baseline.

## Trust CI boundary and holdout patterns

- `trust-ci/holdout.example/validate.py` is the external entrypoint. It imports only the independent M1 holdout validator, performs static source checks for no GitHub Actions, local-grant disclaimers, App/worker separation, policy guards, and AST parsing of selected files. An M2 `architecture_validate.py` should be independently implemented with stdlib only and invoked from this entrypoint; it must never import `.grok-stack/adaptive_grok/architecture.py`.
- `trust-ci/src/adaptive_trust_ci/workspace.py` supplies exact-SHA detached checkout, bounded NUL-safe Git path discovery, no-network command environment, mutation detection, and process-group termination. Architecture holdout selection should consume the checked-out exact diff, not local runtime state.
- `trust-ci/src/adaptive_trust_ci/policy.py` owns server-mounted policy, immutable sandbox, approval globs, command bounds, and external holdout digest. `trust-ci/config/policy.example.json` currently marks `.grok-stack/**`, `trust-ci/**`, and related control-plane paths as `governance`; architecture files at root are not currently covered by that governance glob. Any decision to alter approval coverage is itself a policy/security change and outside a routine M2 model implementation.
- `trust-ci/src/adaptive_trust_ci/models.py` and `runner.py` now carry M1 spec metadata, but no architecture metadata. The approved factory design requires later packet digests to include `architecture_digest`; M2 should publish a stable digest API that M4 can consume without changing Trust CI's authoritative check semantics.

## Recommended bounded M2 slice

1. Add `schemas/architecture.schema.json` with a versioned, strict JSON-compatible model for `system` and `rules`. Require bounded stable IDs and explicit node fields from the roadmap (`id`, `type`, `owner`, `trust_domain`, `data_classification`, `secrets`, `runtime`, `repository_paths`, `public_contracts`) and edge fields (`from`, `to`, `type`, `protocol`, `direction`, `authentication`, `network_policy`, `sync_or_async`, `allowed_data`, `failure_behavior`). Keep `additionalProperties: false` and explicit limits/path safety.
2. Add canonical `architecture/system.yaml` and `architecture/rules.yaml` describing only the existing local stack and Trust CI. Do not add a service, database, queue, framework, deployment, or external integration. Keep README's graph as a decorative projection/test, not a source of truth.
3. Add `.grok-stack/adaptive_grok/architecture.py` as a dependency-free parser/validator/digest module. Reuse M1's bounded JSON parsing/path safety and `util.py` Git/path helpers, but do not import application code or infer architecture from Markdown. Expose deterministic model/rules loading, canonical digest, repository/contract existence checks, architecture diff, post-diff risk classification, and named fitness findings.
4. Add `scripts/grok_architecture.py` with deterministic `validate`, `summary`, `diff`, and `fitness`/JSON output. Explicit paths must remain repository-contained; default paths should resolve to `architecture/system.yaml` and `architecture/rules.yaml` from `find_root`.
5. Integrate a structured architecture check into `.grok-stack/adaptive_grok/verification.py` and report architecture digest/findings in verification evidence. Ensure changed architecture/contracts/rules invalidate receipts or architecture evidence, and ensure post-diff risk never decreases when a new dependency, datastore, secret, network client, or trust-domain edge appears.
6. Add focused tests in `tests/test_architecture_model.py` and `tests/test_architecture_fitness.py` for strict schema/unknown keys, duplicate IDs, unsafe paths, deterministic serialization/digest, missing repository paths/contracts, forbidden edges, trust/secret/network rules, API/event/schema compatibility declarations, migration expand/contract, background-job requirements, diff escalation, and decorative-K16 non-authority.
7. Add `trust-ci/holdout.example/architecture_validate.py`, wire it into `trust-ci/holdout.example/validate.py`, and add holdout tests. The external validator should independently check changed/new architecture model/rules, exact changed paths, stable IDs, declared paths/contracts, forbidden trust/secret/network edges, and no implementation-plus-control-plane mixing. Keep critical rules outside PR-controlled validator code.
8. Update `scripts/install_into.py` and installer tests deliberately: current M1 now copies both `schemas/change-spec.schema.json` and `schemas/change-spec-v1.schema.json` (commits `df30427` onward), but no architecture files. If installed consumers are expected to run architecture CLI/verification, add `architecture/system.yaml`, `architecture/rules.yaml`, and `schemas/architecture.schema.json` to managed files and test a clean target; otherwise explicitly document architecture as root-product-only. `manifest.py`/`package_stack.py` already package ordinary root files but should receive coverage tests for the new paths.

## Critical concerns

- The architecture schema/model is a new authority boundary. Do not make it a permissive graph or allow Markdown/K16 text to override it; unknown versions/keywords, duplicate IDs, unsafe paths, symlinks, missing declarations, and contradictory rules must fail closed.
- The M2 route includes data/API/event/security signals and migration/external-write human gates despite the task's no-new-data/no-external-write scope. Preserve those gates and obtain the selected reviews; do not silently downgrade risk based on implementation size.
- Do not implement architecture validation by importing the local M2 module from Trust CI. The holdout must duplicate critical checks over bytes/data only, as M1 does.
- Avoid modifying `trust-ci/config/policy.example.json` or deployed-policy assumptions as part of model authoring. If architecture-path approval coverage is required, treat it as a separate governed policy decision.
- Architecture digest must be deterministic and later packet-compatible, but M2 must not prematurely create M4 `factory.*`, packet, scheduler, provider, or systemd abstractions. The approved overall design explicitly defers those to later milestones.
