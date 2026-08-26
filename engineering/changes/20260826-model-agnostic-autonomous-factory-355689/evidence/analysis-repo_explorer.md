# Repository analysis — model-agnostic autonomous factory

Route: `35568941ae59`
Change: `20260826-model-agnostic-autonomous-factory-355689`
Snapshot: branch `feature/model-agnostic-factory`, `HEAD`/route base `069fe8226addb8a1922dde3db4e753434baa3a3d`
Scope: read-only repository inventory and M1 design-spec inputs. This report does not propose implementation code or an implementation plan.

## Source-of-truth and sequencing

- The approved user direction is binding: provider-neutral factory core; PostgreSQL durable control plane; at most 20 read/note workers, at most 10 workers per repository, and exactly one application writer; Codex first through `codex exec --json`; Grok compatibility adapter; future adapters through a versioned JSON/JSONL protocol; fixed systemd supervisor/workers; isolated Git worktrees; append-only note broker; bounded leases, retries, runtime, repair, token/cost budgets; and no autonomous external writes.
- Initial hard limits are `readers <= 20`, `per_repo <= 10`, `writers = 1`, infrastructure retries `<= 2`, repair cycles `<= 3`, task wall time `<= 4h`, and task cost `<= $25`.
- Prompt text, repository content, and notes are untrusted data. Repository subprocesses receive no credentials. Provider fallback must never be silent. Chain-of-thought must not be stored.
- Mandatory order is: finish M1; then M2/M3; then M4; then M5; then M6. M7–M9 remain deferred until evidence exists. The current request ends at the design-review gate and explicitly excludes implementation code, an implementation plan, push/PR/merge/release/deploy, and systemd installation.
- The route is high-risk (`ai`, `security`) and names `scope_and_design_approval`; therefore the written specification must stop before implementation pending user review.
- Roadmap M0 text is historically stale relative to the current tree. `README.md` and `decisions.md` record the live App-owned check `adaptive-trust-ci/verified@6737355947c2`, App ID `4694114`, and protected `main`; M0 is therefore an established dependency, not work to repeat in this design slice.

## Existing architecture and reusable assets

### Local workflow plane

- `.grok-stack/adaptive_grok/router.py`, `.grok-stack/config/routing.json`, the route runtime, and `.grok/agents/` already provide deterministic routing, selected read-only analysis/review roles, a single named write role, risk/domain classification, and low-by-default reasoning with high effort reserved for analysis/architecture/security/release roles.
- `.grok-stack/adaptive_grok/change.py`, `.grok-stack/templates/change/`, and `engineering/changes/` provide durable local change-package scaffolding and a lifecycle from `draft` through `ready`/`released`. This is repository-file state, not the future durable background task control plane.
- `.grok-stack/adaptive_grok/verification.py`, `.grok-stack/adaptive_grok/receipts.py`, `scripts/grok_verify.py`, and `scripts/grok_review.py` provide local preflight checks and tree-fingerprint-bound receipts. These receipts contain route ID, kind, status, tree fingerprint, report, and free-form details, but no typed-spec digest or criterion coverage.
- `.grok/hooks/` and `.grok-stack/config/policy.json` provide local usability guardrails around secret reads, protected paths, destructive/production commands, and delegated writes. They are deliberately fail-open and are not merge authority.

### Existing partial M1 typed-spec slice

The roadmap's statement that typed specification is wholly missing is no longer accurate. Commit `48cb973` introduced a bounded initial M1 slice:

- `schemas/change-spec.schema.json`: strict top-level Draft 2020-12-shaped schema, `additionalProperties: false`, stable ID patterns, risk tiers, evidence references, contracts, observability, rollback, and approval scopes.
- `.grok-stack/adaptive_grok/spec.py`: dependency-free restricted-YAML parser/dumper, a deliberately restricted JSON-Schema evaluator, completeness checks, canonical SHA-256 digest, route-derived skeleton generation, summary, and acceptance-criterion evidence mapping.
- `scripts/grok_spec.py`: `generate`, `validate`, `summarize`, and `map` commands.
- `.grok-stack/templates/change/change-spec.yaml`: package template.
- `tests/test_change_spec.py`: schema rejection, YAML tag/anchor/merge rejection, red-risk completeness, non-invented `UNKNOWN` generation, Markdown conflict precedence, CLI behavior, and scope guard tests.
- `scripts/install_into.py` and structure tests know about `schemas/` and `scripts/grok_spec.py`, so these assets already have a distribution seam.

This is a useful parser/schema nucleus, but it does not meet the M1 exit criteria and is not currently a gate.

### Trust and delivery plane

- `trust-ci/` is a separate FastAPI/worker/PostgreSQL service with exact-SHA jobs, idempotency, leases, bounded attempts, signed approvals/attestations, external holdout commands, isolated no-network runners, source-mutation detection, GitHub App publication, metrics, backup/restart drills, and systemd units.
- Its PostgreSQL lease and idempotency patterns are architectural precedent for M4, but `trust_ci.*` must remain separate from future `factory.*`; the roadmap explicitly forbids reusing `trust_ci_jobs` as the factory queue.
- Existing systemd files supervise Trust CI Compose and backup only. There is no factory supervisor/worker unit.

### Assets that do not exist yet

- No `factory/` service or `factory.*` database state.
- No provider-neutral runtime contract, provider registry, Codex adapter, Grok compatibility adapter, or versioned JSON/JSONL adapter schema.
- No fixed factory supervisor/read worker/write worker process definitions.
- No isolated factory worktree manager or durable writer lease.
- No append-only note broker, note provenance/schema, or read/note worker protocol.
- No immutable factory task packet/run manifest, credential broker, workspace network controller, budget/cost accounting, or factory orphan reconciler.
- No semantic finding store, validator/adjudicator contract, or bounded repair engine.

## Precise M1 gaps that the design specification must account for

### Package creation and authority

- `start_change()` merely copies `.grok-stack/templates/change/`; it does not call `generate_spec()`. Its replacement table does not include `OBJECTIVE_STATEMENT`, `RISK_TIER`, or `ROLLBACK_STRATEGY`, so the active package's `change-spec.yaml` still contains literal `{{...}}` placeholders plus `UNKNOWN` values.
- The active `brief.md`, `requirements.md`, `architecture.md`, `test-plan.md`, `release.md`, and `rollback.md` are also mostly empty scaffolds. The design must make the typed spec authoritative and make Markdown a linked explanation/projection rather than a competing requirements source.
- `grok_spec validate` is standalone. `grok_verify`, package state transitions, stop gates, and review receipt creation do not invoke it. A standard/high-risk package can therefore advance while its typed spec is missing, placeholder-filled, stale, or incomplete.

### Completeness and traceability

- The schema allows empty `acceptance_criteria`, `invariants`, `forbidden_outcomes`, and `observability` arrays. Completeness currently requires evidence only for acceptance criteria that already exist; red risk adds only non-empty forbidden outcomes and approval scopes.
- Evidence references are syntax-checked strings only. The current code does not establish that a referenced test/report/receipt exists, ran against the current tree/head, is independent, or actually proves the named criterion.
- `map_evidence()` maps acceptance criteria only. Invariant, forbidden-outcome, objective/production-signal, contract, and approval traceability is absent.
- Local verification receipts do not carry criterion IDs or the canonical spec digest. Tree fingerprinting detects repository changes locally, but no binding to base SHA, head SHA, policy digest, architecture digest, or contract digest exists.
- There is no explicit, machine-enforced documentation-only micro-change exemption.

### Trust CI integration

- `AttestationPayload` schema version 1 contains job/repository/PR/base SHA/head SHA/policy digest, command results, changed files, approval scopes, timing, and signer. It has no typed-spec digest or criterion coverage summary.
- `trust-ci/holdout.example/validate.py` has no change-spec validation. The policy's external holdout command is the correct independent integration seam, but deployed holdout/policy remain outside pull-request control.
- Approval vocabulary is not aligned: the change-spec schema accepts `security`, `data`, `architecture`, `release`, and `protected-path`, while the Trust CI example policy derives `governance`, `database`, and `production`. The design must define an explicit versioned mapping or a single canonical scope vocabulary; silent translation would weaken fail-closed behavior.
- The spec digest is computed from canonical parsed JSON, which is a sound starting point, but the signed attestation and exact-SHA stale-state rules do not consume it yet.

### Security and untrusted-input model

- The restricted YAML parser already rejects tags, anchors, aliases, merge keys, duplicate keys, and unsupported schema keywords. This is a useful fail-closed parser boundary.
- The typed model does not yet express the approved trust invariants for prompt/repository/note data, provider outputs, credentials, network egress, external writes, role capabilities, note provenance, or chain-of-thought exclusion. These must be explicit invariant/forbidden-outcome inputs to the design, not left to prompts.
- The schema's evidence `ref` pattern is path-like, but there is no containment/existence check. Future consumers must not interpret evidence references or note content as executable commands or instructions.

## M1 design-spec inputs to freeze for downstream milestones

The design should treat the following as stable typed intent inputs that later milestones consume without redefining them:

1. **Outcome and boundary:** a local, model-agnostic software factory that produces bounded repository changes and evidence, never autonomous external side effects.
2. **Role/capability invariants:** up to 20 read/note workers globally, up to 10 per repository, exactly one application writer enforced by durable ownership, independent read-only reviewers/validators, and no implementer self-approval.
3. **Provider semantics:** provider-neutral core; explicit adapter identity and protocol version; Codex first via `codex exec --json`; Grok compatibility adapter; future JSON/JSONL adapters; explicit unsupported-capability failure; no silent provider fallback.
4. **Isolation semantics:** isolated worktree per task; task/repository separation; sanitized subprocess environment; no repository-subprocess credentials; no Trust CI/human/production trust material; no network by default and only explicitly recorded allowlists where later authorized.
5. **Data semantics:** PostgreSQL durable control state in a factory-owned schema/database; immutable task packet and run manifest digests; append-only notes with provenance and size limits; no raw chain-of-thought or private reasoning persistence; structured outputs only.
6. **Boundedness:** hard reader/per-repository/writer limits; infrastructure retries at most 2; repair cycles at most 3; wall time at most 4 hours; cost at most USD 25; bounded tokens, leases, output, notes, queues, and retention; explicit stop/escalation states.
7. **External-action boundary:** factory tasks may operate only inside the authorized local repository/worktree during the initial milestones. Push, PR, merge, release, deploy, systemd installation, production mutation, and other external writes require a later separately delegated action and applicable external approval; none are autonomous in this design gate.
8. **Evidence model:** stable IDs for objectives, acceptance criteria, invariants, forbidden outcomes, production signals, and approval scopes; every required criterion maps to independent exact-state evidence; spec digest and coverage become inputs to later M4 task records, M5 task packets/run manifests, M6 findings/verdicts, and Trust CI attestation.
9. **Human gate:** scope/design approval is a durable explicit transition; lack of approval is not a retryable provider failure and must never trigger fallback or implementation.

## Integration seams and roadmap dependencies

| Seam | Current producer/consumer | Design dependency |
| --- | --- | --- |
| Route to typed spec | active route -> `generate_spec()`/package | M1 must define safe route-derived fields, explicit unknowns, and human-filled fields without invention. |
| Typed spec to local gate | `change-spec.yaml` -> `grok_verify`/receipts | M1 must make validity, completeness, digest, and criterion coverage fail-closed for standard/high-risk work. |
| Typed spec to Trust CI | spec digest/coverage -> holdout and signed attestation | M1 contract must be stable before external enforcement; repository code cannot control deployed holdout/policy authority. |
| Typed spec to architecture | contracts/invariants/risk -> M2 architecture model/fitness rules | M2 follows M1 and must reference stable IDs/digests rather than duplicate requirements. |
| Typed spec to governance | evidence/decisions/debt -> M3 reviewed rule lifecycle | M3 cannot allow notes or agent observations to become active policy directly. |
| Typed spec to factory tasks | change/spec/architecture IDs and digests -> M4 durable task rows | M4 follows completed M1–M3; it must not invent replacement intent fields or reuse `trust_ci_jobs`. |
| Typed spec to execution | criteria, roles, limits, allowed capabilities -> M5 immutable packet | M5 follows M4; provider adapters and worktree/systemd execution remain out of M1 implementation. |
| Typed spec to semantic repair | criteria/invariants/forbidden outcomes -> M6 findings and verdicts | M6 follows M5; repair remains same-writer and capped at three cycles. |
| Distribution | schema/template/library/CLI -> installer/package/manifest tests | Any M1 contract surface must remain present in installed copies without adding a root packaging marker. |

## Design-review risks and contradictions to resolve explicitly

- **Partial M1 vs roadmap wording:** current M1 parser/schema/CLI assets exist, while roadmap gap analysis says typed specification is missing. The design should describe M1 as incomplete integration/traceability work, not as a greenfield subsystem and not as completed.
- **Route task vs current user gate:** the persisted route says “architect and implement,” but the current user-authorized scope is design/docs only and stops at review. User-approved scope takes precedence; no write-agent implementation should begin.
- **Package risk placeholder vs route:** route risk is high and maps to typed tier `red`, but the active package still has `{{RISK_TIER}}`. The package must not be represented as valid evidence until the write owner fills and validates it.
- **Approval vocabulary mismatch:** change-spec and Trust CI scope enums are currently different and need a fail-closed contract decision before attestation linkage.
- **Local receipts vs merge authority:** criterion-bearing local receipts will remain preflight only. The App-owned exact-SHA policy-epoch Check Run and signed external attestation remain the merge authority.
- **Reusable Trust CI patterns vs trust-domain separation:** PostgreSQL leases, idempotency, isolated runner patterns, and systemd conventions are reusable ideas; the Trust CI queue, signing keys, App credentials, deployed policy, holdout, and database state are not reusable factory resources.

## Repository conclusion

The repository already has a sound minimal M1 parser/schema/CLI nucleus and mature Trust CI patterns, but it lacks the binding path from route -> complete typed spec -> criterion-aware local evidence -> independent holdout -> signed exact-SHA attestation. The approved design should close that M1 contract first, then define M2/M3 dependencies, while treating M4–M6 as downstream architecture and keeping M7–M9 out of scope until evidence exists.
