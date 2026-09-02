# M5 Isolated Provider Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a provider-neutral, fixture-tested, persistence-integrated M5 execution source plane while preserving factual M4 claim semantics and explicitly blocking unavailable OS-isolation exit evidence.

**Architecture:** Pure immutable contracts and a bounded protocol parser define the trust boundary before persistence. Exact-version fixture adapters feed proposal/workspace brokers; additive migration `013` and new execution endpoints bind every mutation to the existing M4 task/run/owner/fence/allocation/deadline/budget invariants. Source-controlled systemd units and fake-runtime tests are locally verifiable, while live provider and rootless-host operations stay absent.

**Tech Stack:** Python 3.11+, frozen dataclasses, canonical JSON/JSONL, JSON Schema 2020-12, FastAPI, PostgreSQL 15+, `unittest`, source-controlled systemd units.

**Spec:** `docs/superpowers/specs/2026-09-01-m5-isolated-provider-execution-design.md`

## Global Constraints

- Exact current M4 review base is `460a8a01a6394cac710b4e3f9eea3d94d4beef89`; route is `37b05f579320`; branch is `milestone/m5-isolated-execution-provisional-m4`. The original provisional anchor `94fc5ad878e6b15df6418303caada49a3b93bf4c` is superseded for implementation and retained only as restack lineage.
- Delivery target is `2026-09-08 00:00 UTC+3`; calendar pressure cannot waive tests, independent review, external Trust CI, or the dedicated rootless-host exit gate.
- Keep `/v1/claims` legacy semantics: its `packet_digest` remains the M4 `intent_digest`; use new execution endpoints and a new canonical packet digest.
- Preserve M4 ceilings and authority: 20 global readers, 10 readers per repository, one writer, four hours, USD 25, and initial attempt plus two infrastructure retries.
- Codex candidate is exact `0.152.1` / `b8201824…06f9`; Grok candidate is exact `1.0.17` / `82595e26…4568` and remains ineligible until full required conformance passes.
- No credentials, live provider/network calls, fallback, repository subprocess, external write, push/PR/merge/deploy, Trust CI/human-key access, systemd installation/activation, or existing-database migration.
- No raw prompt, native stream, chain-of-thought, scratchpad, unrestricted stdout/stderr, or secret value crosses the durable boundary.
- Host rootless isolation exit is `BLOCKED`: required tools are absent and unprivileged user namespaces are `EPERM`; fake-runtime results cannot satisfy that exit.
- M5 and M6 may develop in parallel but integrate in dependency order. M5 exports digest-bound factual bridge inputs and does not invent M6's schema.
- M7-M9 are roadmap-only consumers: M6 verdict -> M7 shadow bundle/cohort -> M8 at least 30 human-accepted outcomes with demotion and L2 ceiling -> M9 preview/staging/canary/recovery; production remains human-owned.

## File Map

- `factory/contracts/schemas/{task-packet,execution-invocation,execution-event}.v1.json`: closed canonical wire contracts.
- `factory/src/adaptive_factory/execution_contracts.py`: immutable authority/profile/policy/plan/packet/manifest/proposal values.
- `factory/src/adaptive_factory/protocol.py`: bounded strict JSON/JSONL lifecycle parser.
- `factory/src/adaptive_factory/adapters/{base,codex,grok}.py`: fixture-only native translators and eligibility.
- `factory/tests/fixtures/{codex-0.152.1,grok-1.0.17}/`: safe native fixture streams and expected canonical events.
- `factory/src/adaptive_factory/brokers.py`: note/artifact/usage/terminal validation and redaction.
- `factory/src/adaptive_factory/workspace.py`: workspace/Git protocols, fake runtime and host capability report.
- `factory/src/adaptive_factory/resources/013_execution_plane.sql`: additive execution persistence and capabilities.
- `factory/src/adaptive_factory/{models,store,service,api}.py`: execution projections, transactions/use cases and endpoints.
- `factory/src/adaptive_factory/recovery.py`: bounded orphan reconciliation.
- `factory/systemd/`: predefined supervisor/reader/writer/broker source units.
- `factory/tests/test_{execution_contracts,protocol,adapters,brokers,workspace,execution_service,systemd_units}.py`: TDD evidence.
- `README.md`, `factory/README.md`, `DARK_FACTORY_ROADMAP.md`, architecture/installer/current M5 docs: factual parity and connected navigation.

---

### Task 1: Freeze schemas, packet values and manifest identity

**Files:**
- Create: `factory/contracts/schemas/task-packet.v1.json`
- Create: `factory/contracts/schemas/execution-invocation.v1.json`
- Create: `factory/contracts/schemas/execution-event.v1.json`
- Create: `factory/src/adaptive_factory/execution_contracts.py`
- Create: `factory/tests/test_execution_contracts.py`

**Interfaces:**
- Consumes: `TaskIntakeV1`, `LeaseGrant`, trusted execution selection and M4 remaining limits.
- Produces: `AuthorityBindingV1`, `ProviderProfileV1`, `CapabilityPolicyV1`, `ExecutionPlanV1`, `TaskPacketV1.from_selection(...)`, `RunManifestV1.from_packet(...)`, `ExecutionContractError(code)`.

- [ ] **Step 1: Write failing immutable/canonical/closed/bound tests.** Use literal valid values and assert nested inputs cannot mutate packet bytes, packet digest differs from the literal legacy intent digest, unknown fields and excessive limits fail, and the three JSON Schemas accept exactly the canonical examples.
- [ ] **Step 2: Confirm RED.** Run `PYTHONPATH=factory/src python3 -m unittest factory.tests.test_execution_contracts -v`; expect import failure for `adaptive_factory.execution_contracts`.
- [ ] **Step 3: Implement minimal frozen contracts and schemas.** Canonicalize tuples only, reject mutable mappings after parsing, validate NFC/Unicode scalar/digests/IDs/bounds, and domain-separate packet/manifest digests.
- [ ] **Step 4: Confirm GREEN.** Run the command from Step 2; expect every execution contract test to pass.
- [ ] **Step 5: Commit.** `git add factory/contracts/schemas factory/src/adaptive_factory/execution_contracts.py factory/tests/test_execution_contracts.py && git commit -m "feat(factory): freeze M5 execution contracts"`.

### Task 2: Enforce protocol lifecycle and exact-version fixture adapters

**Files:**
- Create: `factory/src/adaptive_factory/protocol.py`
- Create: `factory/src/adaptive_factory/adapters/__init__.py`
- Create: `factory/src/adaptive_factory/adapters/base.py`
- Create: `factory/src/adaptive_factory/adapters/codex.py`
- Create: `factory/src/adaptive_factory/adapters/grok.py`
- Create: `factory/tests/fixtures/codex-0.152.1/*.jsonl`
- Create: `factory/tests/fixtures/grok-1.0.17/*.jsonl`
- Create: `factory/tests/test_protocol.py`
- Create: `factory/tests/test_adapters.py`

**Interfaces:**
- Consumes: bounded bytes plus expected task/run/packet/profile identity.
- Produces: `ProtocolLimits`, `CanonicalEvent`, `EventStreamParser.feed()/finish()`, `AdapterConformance`, and fixture-only `CodexAdapter.translate()` / `GrokAdapter.translate()`.

- [ ] **Step 1: Write failing parser/adversarial tests.** Cover duplicate JSON keys, non-finite values, invalid UTF-8/scalars, long line/stream, event flood, identity/sequence mismatch, reasoning keys, output after terminal, missing/duplicate terminal and undeclared event capability.
- [ ] **Step 2: Confirm RED.** Run `PYTHONPATH=factory/src python3 -m unittest factory.tests.test_protocol -v`; expect missing protocol module.
- [ ] **Step 3: Implement the bounded incremental parser.** Decode one line at a time with strict object-pairs and constant rejection codes; retain only canonical allowlisted payloads and one terminal.
- [ ] **Step 4: Write and confirm failing adapter tests.** Assert exact Codex/Grok identities, native reasoning removal, canonical literal outputs, no callable subprocess/network method, no fallback registry path, Codex fixture eligibility and Grok ineligibility.
- [ ] **Step 5: Implement minimal fixture translators and conformance.** Native types map through explicit tables; unknown or version-mismatched input fails closed.
- [ ] **Step 6: Confirm GREEN and commit.** Run `PYTHONPATH=factory/src python3 -m unittest factory.tests.test_protocol factory.tests.test_adapters -v`, then commit with `feat(factory): add bounded provider fixture adapters`.

### Task 3: Add proposal brokers and fake workspace/Git boundary

**Files:**
- Create: `factory/src/adaptive_factory/brokers.py`
- Create: `factory/src/adaptive_factory/workspace.py`
- Create: `factory/tests/test_brokers.py`
- Create: `factory/tests/test_workspace.py`

**Interfaces:**
- Consumes: canonical events, `TaskPacketV1`, current lease identity and opaque workspace handles.
- Produces: `ProposalBroker.accept(event, context)`, `WorkspacePolicy`, `WorkspaceHandle`, `FakeWorkspaceBroker`, `FakeGitBroker`, `HostIsolationReport.probe(command_lookup, userns_probe)`.

- [ ] **Step 1: Write failing broker tests.** Each test names the break: stale fence accepted, role impersonation accepted, executable note stored, artifact traversal accepted, missing usage treated as zero, duplicate terminal accepted, or reasoning text retained.
- [ ] **Step 2: Confirm RED.** Run `PYTHONPATH=factory/src python3 -m unittest factory.tests.test_brokers -v`; expect missing broker module.
- [ ] **Step 3: Implement minimal typed proposal validation.** Return immutable proposals or stable rejection codes; redact before creating a durable value.
- [ ] **Step 4: Write and confirm failing workspace tests.** Exercise traversal, absolute/symlink/shared `.git`, cross-task handles, credential-shaped environment keys, nonempty egress, external Git operations and deterministic blocked host report.
- [ ] **Step 5: Implement capability protocols/fakes/probe.** Do not invoke a repository command or create a real namespace; the injected probe makes behavior deterministic.
- [ ] **Step 6: Confirm GREEN and commit.** Run both test modules and commit with `feat(factory): enforce execution broker boundaries`.

### Task 4: Add migration 013 and explicit execution service/API

**Files:**
- Create: `factory/src/adaptive_factory/resources/013_execution_plane.sql`
- Modify: `factory/src/adaptive_factory/models.py`
- Modify: `factory/src/adaptive_factory/store.py`
- Modify: `factory/src/adaptive_factory/service.py`
- Modify: `factory/src/adaptive_factory/api.py`
- Modify: `factory/contracts/openapi/factory-control.v1.json`
- Create: `factory/tests/test_execution_service.py`
- Modify: `factory/tests/test_migrations.py`
- Modify: `factory/tests/test_api.py`

**Interfaces:**
- Consumes: current authenticated worker, execution selection, M4 claim/fence/allocation and canonical proposal values.
- Produces: `ExecutionGrant`, `ExecutionStage`, `claim_execution`, `advance_execution`, `commit_execution_proposal`, and six `/v1/execution/*` endpoints.

- [ ] **Step 1: Write failing migration/legacy tests.** Assert versions are `1..13`, migration 013 only creates/adds/revokes/grants, and existing `/v1/claims` response and `packet_digest=intent_digest` fixture are unchanged.
- [ ] **Step 2: Confirm RED.** Run `PYTHONPATH=factory/src python3 -m unittest factory.tests.test_migrations factory.tests.test_execution_service -v`; expect migration/version and missing execution failures.
- [ ] **Step 3: Implement additive schema and pure fake-store vertical slice.** Persist immutable packet/manifest first, append stages/proposals, and validate every operation against live task/run/owner/fence/allocation/packet/deadline/budget/idempotency.
- [ ] **Step 4: Write failing API contract tests.** Cover auth/scope/repository/body bounds, exact responses, idempotency conflict, stale fence and absence of provider-native or secret fields.
- [ ] **Step 5: Implement thin endpoints/OpenAPI.** Reuse M4 authentication/error/correlation boundaries; never accept executable/provider path or environment fields.
- [ ] **Step 6: Confirm GREEN and commit.** Run the three focused modules plus existing service/API tests, then commit with `feat(factory): integrate fenced execution lifecycle`.

### Task 5: Recover orphans, expose bounded metrics and freeze systemd sources

**Files:**
- Create: `factory/src/adaptive_factory/recovery.py`
- Create: `factory/systemd/adaptive-factory-supervisor.service`
- Create: `factory/systemd/adaptive-factory-reader@.service`
- Create: `factory/systemd/adaptive-factory-writer.service`
- Create: `factory/systemd/adaptive-factory-broker.service`
- Create: `factory/tests/test_systemd_units.py`
- Modify: `factory/tests/test_execution_service.py`
- Modify: `factory/tests/test_postgres_integration.py`

**Interfaces:**
- Consumes: keyset cursor, max `100`, database time, current M4 live allocation/fence evidence.
- Produces: `ExecutionRecovery.reconcile(limit, cursor)`, fixed execution metric families, static hardened units.

- [ ] **Step 1: Write failing recovery tests.** Assert ordered bounded scan, live manifest preservation, stale manifest orphaning once, late event rejection, cleanup failure retention and replay idempotency.
- [ ] **Step 2: Confirm RED.** Run the exact recovery cases in `factory.tests.test_execution_service`; expect missing recovery behavior.
- [ ] **Step 3: Implement minimal recovery and fixed metrics.** No dynamic label/key surface; protocol/proposal/orphan outcomes are fixed fields.
- [ ] **Step 4: Write failing unit topology tests.** Parse unit sections and assert fixed users/commands, no task interpolation, hardening/resource/restart values and no install/enable section.
- [ ] **Step 5: Add units, confirm GREEN and commit.** Run recovery/systemd tests and locally available migration/integration checks; commit with `feat(factory): add restart-safe execution topology`.

### Task 6: Connect current docs, architecture, installer and M6 bridge

**Files:**
- Modify: `README.md`
- Modify: `factory/README.md`
- Modify: `DARK_FACTORY_ROADMAP.md`
- Modify: `architecture/system.yaml`
- Modify: `architecture/rules.yaml`
- Modify: `scripts/install_into.py`
- Modify: `tests/test_structure.py`
- Modify: `tests/test_architecture_model.py`
- Modify: this plan and the active package ledger/schedule/release/rollback/evidence index.

**Interfaces:**
- Consumes: final source inventory and exact provisional status.
- Produces: bidirectional current-doc links, complete README graph, factual M4→M5→M6 interface map, installer inventory and parity checks.

- [ ] **Step 1: Write failing doc/architecture parity tests.** Remove one expected M5-M9 link/node/contract in a controlled fixture and assert orphan/staleness failure; require deadline, branch, route, base, blocker, exact digest/SHA invalidation, rollback, forbidden-authority and no-exit wording.
- [ ] **Step 2: Confirm RED.** Run `python3 -m unittest tests.test_structure tests.test_architecture_model -v`; expect missing current M5 inventory/link failures.
- [ ] **Step 3: Update current docs and models only.** Do not rewrite historical evidence. Preserve every edge in the root README complete stack graph and add the factual M6 digest boundary without a new M6 schema.
- [ ] **Step 4: Update installer managed source inventory.** It may copy M5 source/contracts/units but must never install/enable units, migrate a database, or create provider credentials.
- [ ] **Step 5: Confirm GREEN and commit.** Run the Step 2 command plus installer tests; commit with `docs(m5): connect provisional execution source map`.

### Task 7: Final locally feasible verification and blocked exit record

**Files:**
- Modify: active package `tasks.md`, `test-plan.md`, `release.md`, `rollback.md`, `evidence/README.md` and `schedule.md`.
- Modify: `decisions.md` only for a proven reusable decision.
- Modify: `mistakes.md` only if an actual mistake caused a problem.

**Interfaces:**
- Consumes: final diff and fresh command output.
- Produces: exact source status, focused command ledger, OS-isolation `BLOCKED` statement and parent handoff.

- [ ] **Step 1: Run all focused factory unit tests.** `PYTHONPATH=factory/src python3 -m unittest discover -s factory/tests -v`; record exit/count.
- [ ] **Step 2: Run every locally available disposable PostgreSQL/API check.** Use only the existing safe harness; record unavailable rootless/container capability as blocked rather than success.
- [ ] **Step 3: Run root checks.** `python3 -m unittest tests.test_structure tests.test_architecture_model tests.test_installer -v`, then `python3 scripts/grok_verify.py --mode pr` only after the last product/doc edit.
- [ ] **Step 4: Re-read the design and acceptance criteria.** Mark only locally evidenced source criteria; leave independent review/receipt and rootless host exit open.
- [ ] **Step 5: Commit evidence docs.** Commit with `docs(m5): record provisional source verification`; do not claim M5 exit.
- [ ] **Step 6: Hand off to parent.** Report commits, commands/results, residual rootless-host blocker and M6 bridge inputs. Parent owns review dispatch, receipts and any external action.
