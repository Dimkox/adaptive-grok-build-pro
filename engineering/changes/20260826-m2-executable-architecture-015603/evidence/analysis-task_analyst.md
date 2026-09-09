# M2 task analysis — executable architecture and fitness functions

## Delivery ruling

M2 is a **versioned, machine-readable architecture contract plus deterministic, independent fitness enforcement** for the current local stack and Trust CI source.  It replaces the README K16 clique as architecture authority; the K16 graph remains a decorative/inventory regression only.  M2 consumes the completed M1 v2 typed-spec/digest/receipt/holdout interfaces and publishes an architecture digest for later M4 immutable task packets.  It must not create the factory control plane, a database/service/queue, provider adapter, systemd unit, external integration, or external write capability.

The current `architecture/` directory is absent and the M2 package is only a generated draft.  The first vertical slice must therefore create the contract, model, parser, and tests before adding verification/holdout integration.

## Critical prerequisite: establish an M2-only baseline

The active route records `base_commit=069fe822…`, while this worktree has subsequent commits closing the M1 source/evidence.  Using the route base directly for architecture diff, changed-path discovery, and post-diff risk would misattribute all M1 changes to M2.  Before implementation, record the exact completed-M1 parent SHA and tree fingerprint as the M2 architecture-diff baseline in the change package/route evidence; do not silently overwrite historical M1 receipts.  Every M2 architecture diff, risk result, holdout invocation, and receipt must bind to that exact base and final head.

## Explicit acceptance criteria

### A. Architecture model and strict schemas

1. `architecture/system.yaml` and `architecture/rules.yaml` are canonical, bounded UTF-8 JSON text despite the `.yaml` suffix, with separate explicit schema versions and a checked-in strict Draft 2020-12 schema (or schemas).  Duplicate JSON keys, non-finite numbers, BOM/trailing data, unsafe/symlink/non-regular paths, excessive input size/depth/nodes, unknown future versions, and unknown authoritative properties fail closed with path-qualified findings.
2. Every current architectural node declares exactly the roadmap-required fields: stable `id`, `type`, `owner`, `trust_domain`, `data_classification`, `secrets`, `runtime`, repository-contained `repository_paths`, and `public_contracts`.  It models only current local workflow/Trust-CI source components; it does not assert unverified live deployment topology.
3. Every edge declares stable source/destination IDs, `type`, `protocol`, `direction`, `authentication`, `network_policy`, `sync_or_async`, `allowed_data`, and `failure_behavior`.  All references resolve, duplicate/conflicting edges fail, and secrets/data classifications are compatible with the declared trust domains.
4. Rules are declarative, stable-ID records.  They state scope, severity, enforceability, and deterministic matcher/threshold inputs; no arbitrary Python, shell, regex from untrusted data without a bounded supported syntax, network fetch, or model-generated executable rule is accepted.
5. Canonical model/rules digests and generated outputs are byte-stable for semantically identical canonical input and sorted by stable ID/path.  The architecture digest is held in verification/evidence envelopes, not added as a mutable field to M1 intent specs.

### B. Repository truth, diagrams, and change analysis

6. Repository paths and declared OpenAPI/AsyncAPI/JSON-Schema/event references are containment-checked, non-symlinked, existing regular files (or explicitly declared optional/absent where the model permits).  A missing, escaping, stale, or unmodeled declared contract fails drift validation.  Existing empty `engineering/contracts/**/.gitkeep` directories do not fabricate API/event/data contracts.
7. A deterministic CLI validates, summarizes, renders diagrams, checks drift/fitness, and compares exact base/head architecture state.  It works from an explicit root/path without mutable runtime state and emits bounded deterministic JSON for automation.
8. Generated C4 context, container, deployment, data-flow, and trust-boundary diagrams are derived only from the model/rules, contain no manual authoritative edges, and support a `--check`/equivalent byte-for-byte reproducibility assertion.  Text Mermaid/DOT artifacts are sufficient; no image-generation or rendering dependency is required.
9. Architecture diff reports added/removed/changed nodes, edges, contracts, trust/data classifications, and rule changes from the exact M2 base to head.  It must report an empty diff only when canonical model/rules are unchanged, never infer the model from the K16 README graph.
10. Post-diff risk is deterministic and monotonic: `post_risk = max(route_pre_risk, architecture_escalation)`.  A newly introduced edge, secret, network client, datastore, trust-domain crossing, public contract, background job, service, queue, framework, or external integration escalates to the configured higher tier and cancels a documentation exemption.  It cannot lower the routed pre-risk or grant capability/approval automatically.

### C. Fitness and independent enforcement

11. Local fitness checks cover each mandatory roadmap class when applicable: forbidden dependency/edge and module boundary; public API/event/schema compatibility; migration expand-contract; tenant/authorization filtering; undeclared network client; test/governance-to-production import; Trust-CI/holdout mutation mixed with implementation; changed-code size/complexity; background-job idempotency/correlation/observable failure/bounded retry/DLQ; secret trusted-edge flow; and prohibition on runner/factory access to production trust material.
12. For a category not present in the current repository, the result is explicit `not_applicable` with its model predicate and scanned paths—not a silent pass.  If a changed file newly matches a regulated category without a model declaration, the result is fail/escalate, not `not_applicable`.
13. Critical trust-boundary, secret-flow, protected Trust-CI/holdout mixing, and architecture-schema invariants are reimplemented in `trust-ci/holdout.example/architecture_validate.py` and invoked by the holdout entrypoint.  The holdout uses bounded bytes/data/path analysis and does not import `.grok-stack/adaptive_grok.architecture` or execute PR-controlled validator code.
14. PR/release verification records an `architecture` evidence object containing schema/model/rules digest, exact base/head, drift/fitness results, post-risk, and exemption status.  A stale architecture binding invalidates the corresponding verification/review evidence just as M1 invalidates stale spec binding.
15. The M2 change spec is red, complete, gate-valid, and maps all AC/INV/FORBID/SIG items to focused tests, verification/review receipts, and the independent holdout/attestation evidence.  M1 v2 validation, criterion bindings, and old signed-attestation verification remain green.

## Invariants and non-goals

| Invariant / boundary | Ruling |
| --- | --- |
| K16 graph | Preserve current README graph test as inventory only.  Do not derive authoritative edges from its complete clique and do not change it merely to make the model agree. |
| M1 intent authority | `change-spec.yaml` remains typed business intent; M2 architecture/rules digest is a separate exact-state evidence binding.  Neither Markdown nor architecture model overwrites M1 IDs/risk/approvals. |
| Trust boundary | Local architecture checks are preflight only.  Holdout/attestation reads data and stays independent; source changes do not deploy policy, images, keys, trust stores, holdout bundles, or branch protection. |
| No new runtime | No factory directory, root dependency manifest, service, database/migration, queue, framework, provider/Codex/Grok adapter, systemd unit, webhook/API, or external integration. |
| No external writes | No push, PR/comment creation, merge, deploy, production mutation, approval signature, or production/connector write.  Architecture diff can report a required approval but cannot obtain or manufacture it. |
| Future factory compatibility | Stable architecture digest/version is the only M2 output consumed by M4/M5 packet construction.  M2 does not implement leases, 20-reader/one-writer limits, provider protocol, systemd persistence, retries, or repairs. |
| Untrusted input | Model/rules, repository source, contracts, Markdown, logs, and model output are data.  They cannot select command paths, imports, policy locations, external URLs, capabilities, or trusted transitions. |
| Human gates | `scope_and_design_approval` is required before the write slice.  `migration_or_external_write_approval` is not applicable only while the stated no-migration/no-external-write boundary holds; stop and obtain it if scope expands. |

## Dependency order

1. **Freeze scope and baseline.** Record completed-M1 base/head; complete the active M2 typed spec and package design (including the model’s current-source boundary and no-future-factory rule).
2. **Contract-first model.** Add strict architecture schemas, bounded canonical loader/dumper, semantic cross-reference validation, canonical digest, and failing model tests.
3. **Seed current source model.** Model real repository components and real directed data/trust edges: local route/change/spec/verification/receipts and the distinct Trust-CI API, worker, PostgreSQL source, runner, holdout, and GitHub-App integration.  Do not encode the README clique or planned M4/M5 components as existing.
4. **Authoring/inspection CLI.** Add validation, normalized summary, deterministic rendering, and path/contract drift checks; then generate/check diagrams from the same canonical data.
5. **Fitness/diff engine.** Add declarative rule evaluation, changed-path classification, exact-base/head architecture diff, monotonic post-risk, and architecture evidence/staleness in local verification.
6. **Independent enforcement.** Add the separately implemented holdout validator and minimal trusted attestation metadata/evidence integration needed to expose the architecture digest/diff without importing local code.
7. **Complete package and review.** Fill M2 specs/docs/rollback, run all focused/full checks, then route-selected code, test, security, data, and release reviews against one final fingerprint.

## Test matrix

| Area | Required positive and negative proof |
| --- | --- |
| Parser/schema | Valid minimal full system/rules; missing/unknown field; unknown version; duplicate JSON key/ID; unresolved node/edge/contract; unsafe/symlink/non-regular/oversized/deep input; unsupported rule predicate. |
| Canonicalization/digest | Key ordering and input path order produce identical canonical digest/rendering; a semantic model/rule edit changes digest; no mutation during validation/render. |
| Current model/drift | Every modeled repository path exists and is contained; every declared contract resolves; missing/deleted/escaping path fails; `.gitkeep` does not imply an interface. |
| Diagrams | All five required diagram views derive from model; regenerated artifacts exactly match committed output; a changed edge changes only the expected deterministic view/diff. |
| Fitness | One failing and one passing fixture for each mandatory category; explicit not-applicable fixture; changed undeclared API/event/network/datastore/job/secret/trust edge fails or escalates. |
| Risk | Table-driven low/medium/high pre-risk plus each architecture trigger; equal/lower trigger never lowers risk; docs exemption is revoked by an architecture-significant diff. |
| M1 compatibility | M1 v2 current package gate validation, CLI, receipt criterion/fingerprint staleness, legacy unchanged v1 read behavior, and existing signed schema-v1 fixture verification remain passing. |
| Holdout | Source-level no-local-import assertion plus adversarial changed-model/rules fixtures; malformed/missing/drifted critical policy fails before PASS; normal M1 holdout checks remain intact. |
| Trust/verification | Architecture evidence binds exact base/head/digest and becomes stale on model/rules/contract/base/head change; a local architecture pass cannot substitute for App-owned exact-SHA status. |
| Full gate | Root discovery tests; Trust-CI discovery tests; compileall; `grok_verify --mode pr --no-record --json`; then all five route-selected reviews and exact-head external check after authorized PR delivery. |

## Rollback and recovery

- This is source/schema/artifact work only: no migration, backfill, service deployment, or external state mutation.  Recovery is a PR revert to the previous M1-complete source tree; legacy M1 specs/receipts/attestations remain readable.
- A false positive or missing declared edge fails safely: pause M2 architecture enforcement for the affected change only by a new reviewed source change or use the previous immutable deployed holdout/policy.  Do not weaken an external critical rule, rewrite evidence, or silently mark it not applicable.
- If a canonical model or generated diagram becomes corrupt/stale, regenerate solely from the last committed model and compare its digest; never hand-edit a generated artifact to clear a check.
- If an architecture-check/holdout disagreement occurs, preserve both exact inputs and digests, treat the trusted holdout result as the merge-side blocker, and return a bounded correction to the single write owner.

## Ambiguities resolved with bounded rulings

| Ambiguity | Ruling |
| --- | --- |
| `.yaml` versus deterministic implementation | Use canonical JSON stored as `.yaml`, matching M1; no PyYAML/jsonschema dependency. |
| Schema layout | Prefer one strict `schemas/architecture.schema.json` with `$defs` for system/rules or two explicitly versioned schemas.  Do not leave an undocumented schema subset. |
| Diagram format/location | Check in deterministic text artifacts under a dedicated architecture-generated path and verify regeneration; rendered images are non-authoritative and out of scope. |
| Which rules apply to an empty generic repository? | Model applicability explicitly.  Absence yields `not_applicable` only before changed-path classification; a newly introduced relevant artifact must be declared and checked. |
| Generic static analysis cannot prove all language semantics | M2 rules are bounded to supported repository languages/patterns and fail closed/require architecture approval for unsupported new runtime/language constructs; do not claim universal dependency analysis. |
| "Critical rules outside implementer control" while source includes holdout example | The checked-in example and local tests are evidence only.  Independent enforcement is achieved only when the deployed external holdout/policy uses the reviewed rule; PR source cannot assert deployment. |
| Architecture approval versus this route’s red risk | A red typed spec must declare required approval scope and forbidden outcomes.  Route scope/design approval governs source design; it neither creates Trust-CI human approval nor authorizes a migration/external write. |

## Critical concerns for the write owner

1. Re-baseline M2 on the exact completed-M1 parent before implementing architecture diff/risk; otherwise all M2 evidence is contaminated by historical M1 changes.
2. Do not make the K16 clique, Markdown, local receipt, or PR-controlled architecture parser the authority; model/rules plus the independently deployed holdout are the required boundary.
3. Keep the generic fitness engine bounded and applicability-explicit.  A broad “scan all code” rule without supported-language semantics will create either bypasses or false claims of safety.
4. The route is red/high-risk with a design gate; do not begin the `data_implementer` source mutation until the scope/model/rule decisions above are recorded and approved.
