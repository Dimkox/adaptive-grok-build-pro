# Model-Agnostic Autonomous Factory — Design

## Status

Proposed architecture for route `35568941ae59` and change `20260826-model-agnostic-autonomous-factory-355689`. This document freezes scope and interfaces for user review; it does not authorize implementation. The current gate is `scope_and_design_approval`.

## Decision

Build a provider-neutral local software factory whose deterministic control plane owns state, policy, leases, budgets, capabilities, and provider selection. PostgreSQL is the durable source of operational truth; fixed systemd processes claim bounded work; provider-specific adapters translate a versioned JSON/JSONL factory protocol; isolated workspaces and brokers enforce effects outside the model.

Codex is the first provider adapter through `codex exec --json`. Grok is supported by an explicit compatibility adapter. Neither native stream is the factory protocol, neither provider may be selected as a silent fallback, and neither adapter may mutate control-plane state or perform external writes.

## Baseline and authority

- `HEAD` at design start: `069fe8226addb8a1922dde3db4e753434baa3a3d` on `feature/model-agnostic-factory`.
- M0 is an established dependency: the root README records the live App-owned policy-epoch Trust CI check on protected `main`. This design performs no M0 operation.
- Commit `48cb973` provides an initial M1 schema/parser/CLI/test foundation. M1 is not complete until typed intent is bound to criterion-aware local evidence and independent exact-SHA Trust CI evidence.
- The current user-approved scope overrides the broader persisted route wording: this change ends after design/docs, a local commit, and the user review gate.
- Prompt files, repository files, notes, local receipts, adapters, and model output are untrusted and are never merge authority.

## Scope

This design specifies:

- the stable intent and trust invariants M1 must expose to later milestones;
- M2/M3 contracts consumed by the factory;
- the M4 PostgreSQL control-plane boundary and durable semantics;
- the M5 provider protocol, Codex/Grok adapter boundaries, fixed systemd topology, workspaces, note broker, and credential/network isolation;
- the M6 independent semantic verdict and bounded same-writer repair boundary;
- evidence gates that keep M7–M9 unavailable.

## Non-goals

- No implementation code, implementation plan, migration, dependency, `factory/` service, schema, or systemd unit is created by this change.
- No provider invocation, background worker, worktree creation, credential provisioning, or systemd installation occurs.
- No push, pull request, merge, release, deploy, connector call, production mutation, or other external write occurs.
- No GitHub Actions, root packaging marker, auto-merge, autonomous PR creation, preview, canary, or production promotion.
- No reuse of `trust_ci.*`, Trust CI keys, holdout, policy, App credentials, or human trust material for factory orchestration.
- No claim that packet immutability, prompts, JSON validation, or model quality prevents prompt injection. The design reduces risk and bounds effects through controls outside the model.

## Mandatory milestone dependency

```text
M0 established
  -> finish M1 typed intent and evidence traceability
  -> complete M2 executable architecture and M3 controlled knowledge/debt
  -> M4 durable factory control plane
  -> M5 isolated execution, provider adapters, Codex, Grok, systemd
  -> M6 independent semantic validation and bounded repair
  -> M7-M9 only after their required evidence and a separate approval
```

M2 and M3 may proceed after M1, but M4 starts only when both publish stable versioned contracts. No later milestone may be used to declare an earlier milestone complete. Through M6, the terminal product is a local branch/commit/evidence bundle for a human; external-write capabilities remain absent.

## Architectural invariants

1. Provider-neutral core: provider identities and native event shapes do not appear in core state transitions or policy logic.
2. One application writer: exactly one valid global writer lease exists at a time; all readers, reviewers, and validators are read-only and may append only through approved brokers.
3. Bounded concurrency: read/note workers are at most 20 globally and at most 10 for one repository. These are ceilings, not staffing targets.
4. Bounded loops: infrastructure retries are at most two after the initial attempt; semantic repair cycles are at most three; aggregate task wall time is at most four hours; aggregate provider cost is at most USD 25.
5. Explicit provider choice: provider, adapter, native CLI/API version, model, and factory protocol version are persisted before dispatch. Unavailability or incompatibility produces a typed failure or `needs_human`, never fallback.
6. Untrusted content: prompt, repository, notes, logs, retrieved data, tool output, native provider events, and model results cannot change policy, role, tools, paths, network, provider, budget, or acceptance criteria.
7. No credential inheritance: repository subprocesses receive no provider, factory, Trust CI, human-approval, production, or external-write credential.
8. No network by default: repository subprocesses have no egress. Provider transport has only its operator-reviewed destination policy and is isolated from repository tools.
9. No autonomous external writes: adapters and workers have no push, PR, merge, release, deploy, connector, systemd-install, or production capability.
10. No chain-of-thought storage: raw reasoning, scratchpads, unrestricted prompts, native streams, and unrestricted stdout/stderr do not cross the durable boundary.
11. Exact-state evidence: packets, findings, artifacts, notes, results, approvals, and receipts bind to immutable digests, applicable exact SHA values, and lease generations.
12. Trust separation: factory output is a proposal; only independent Trust CI may publish the authoritative App-owned exact-SHA verdict.

## Four planes

```text
Intent plane (M1-M3)
  typed spec + architecture model/rules + reviewed governance/debt
                    |
                    v immutable IDs and digests
Factory control plane (M4)
  API/intake -> supervisor/scheduler -> PostgreSQL factory.*
                    |
                    v fenced leases and immutable packets
Factory execution plane (M5-M6)
  workspace/tool broker -> provider adapter -> read/note workers or one writer
                    |
                    v local diff, artifacts, findings, usage, verdict
Trust and delivery plane
  independent Trust CI -> App-owned exact-SHA check -> human-owned delivery
```

The execution plane cannot update task state directly. It emits validated proposals; the control plane applies allowed transitions transactionally after checking identity, packet digest, lease fence, budget, and terminal semantics.

## Component boundaries

| Component | Owns | Must not own |
| --- | --- | --- |
| Intent validator | Schema validity, stable IDs, completeness, canonical digest, criterion mappings | Runtime leases, provider choice, secrets |
| Architecture/governance validators | Versioned component/trust/data-flow rules and reviewed policy/debt lifecycle | Runtime execution or self-activation from agent notes |
| Factory API | Authenticated local/manual intake, idempotency, immutable accepted intent | Repository commands, provider-native parsing, external writes |
| Supervisor/scheduler | Dispatch, capacity, WIP, kill switches, deadlines, reconciliation | Provider credentials, workspace file writes, Trust CI verdicts |
| PostgreSQL `factory.*` | Tasks, runs, fences, attempts, notes, usage/cost, audit, projections | `trust_ci.*` state and secret bodies |
| Packet builder | Canonical packet bytes and digest from approved durable fields | Mutable chat history or credentials |
| Workspace/tool broker | Exact-state workspace, Git mediation, path/tool/environment/network enforcement | Provider selection, acceptance decision, external authority |
| Provider adapter | Native invocation translation and allowlisted event normalization | Database access, scheduling, fallback, policy changes, state mutation |
| Note broker | Append-only bounded notes with provenance and evidence references | Instructions, mutable shared memory, policy/task mutation |
| Semantic validator/adjudicator | Independent requirement-level findings and `pass/repair/needs_human` recommendation | Writer capability, implementer reasoning, Trust CI publication |
| Trust CI | Independent exact-SHA verification and authoritative App check | Factory implementation or task scheduling |

## M1 completion contract

The existing M1 foundation becomes complete only when all of these are independently evidenced:

- every standard/high-risk package has one schema-valid, complete, placeholder-free canonical `change-spec.yaml`;
- stable IDs cover objectives, acceptance criteria, invariants, forbidden outcomes, signals, and approval scopes;
- evidence references are repository-contained, path-safe, resolvable, and bound to actual execution rather than treated as proof by filename;
- local verification/review receipts include canonical spec digest, covered criterion IDs, exact fingerprint, and applicable SHA values;
- staleness is triggered by relevant spec, contract, architecture, policy, base/head SHA, or evidence changes;
- the external holdout independently rejects missing, malformed, incomplete, path-unsafe, or stale required specs;
- signed Trust CI attestations include the independently derived spec digest and criterion coverage summary;
- documentation-only micro exemptions are explicit, machine-readable, exact-state-bound, expiring, and unavailable to red-risk, AI/security, factory/trust/governance, executable-doc, contract, generated-code, or mixed diffs;
- schema evolution and historical adoption are explicit and tested; unknown future versions fail closed;
- Markdown links to or explains typed authority and cannot override it.

This design package is a concrete consumer of M1 and is schema-valid, but it does not by itself prove all repository-wide M1 exit criteria. M1 completion remains the first post-review milestone.

## Immutable task packet

The packet is a canonical, size-bounded object produced from approved durable records. Its digest covers:

- protocol and packet schema versions;
- task, run, repository, route, and change identities;
- exact base SHA and current head SHA when a writer result exists;
- spec, architecture, governance/policy, prompt-template, role-definition, tool-policy, and output-schema digests;
- selected role, reasoning effort, provider, adapter, native runtime, and model identities;
- allowed paths, tools, network destinations, and artifact classes;
- acceptance criterion IDs and expected structured output;
- hard wall, token, cost, event, output, note, artifact, and repair limits.

Untrusted content is placed in a separately labelled envelope with origin, digest, size, and retention class. It is data, not control. Any change to a control field creates a new packet and run; a packet is never edited in place. Repairs use fresh contexts reconstructed from durable state and structured findings, not accumulated chat transcripts.

Packets never contain database credentials, provider secrets, Trust CI material, human approval keys, production credentials, or external-write capability.

## Provider-neutral adapter protocol

### Process contract

```text
operator-configured fixed executable
stdin  = exactly one bounded canonical JSON invocation
stdout = bounded canonical JSONL event stream
stderr = bounded redacted diagnostics, never protocol
exit   = allowed exit code plus exactly one terminal event
```

The protocol has its own exact major/schema version. Adapter version, provider identity, native CLI/API version, and model identity are separate fields. Unknown major/schema, missing required capability, or ambiguous compatibility fails closed.

### Invocation envelope

The conceptual envelope contains:

```text
protocol_version, message_type=invoke
task_id, run_id, attempt, role
packet_digest, spec_digest, architecture_digest
repository_id, exact_base_sha, workspace_handle
provider_id, adapter_id, adapter_version, native_version, model_id
capability_profile, acceptance_ids, output_schema_digest
deadline, token_budget, cost_budget_usd, event/output bounds
```

Only the trusted launcher supplies the executable and provider configuration. No field derived from untrusted content becomes a command-line option, executable path, environment variable name, unit name, database locator, or network policy.

### Canonical events

Allowlisted event classes are:

- `adapter.ready`: identity, versions, and capabilities;
- `run.started` and bounded lifecycle status;
- `note.proposed`: concise conclusion plus evidence references;
- `finding.proposed`: typed requirement-level finding;
- `artifact.proposed`: content-addressed artifact reference;
- `usage.reported`: trustworthy metering fields and provenance;
- exactly one `run.completed`, `run.failed`, or `run.needs_human` terminal event.

Every event carries protocol version, task/run identity, producer sequence, type, and bounded payload. The broker adds trusted receive time and durable sequence. Malformed or oversized JSON, identity mismatch, unknown required type, non-monotonic or duplicate sequence, undeclared capability, invalid artifact reference, missing or duplicate terminal event, or output after termination is a protocol violation and ends the run fail-closed.

Raw provider events do not become canonical events automatically. The adapter validates, allowlists, normalizes, and redacts a minimal projection. Reasoning/scratchpad event classes are discarded before durable storage. If an adapter cannot separate private reasoning or cannot supply a required structured result, cancellation, usage, or isolation property, it is ineligible for that role.

## Codex adapter

The first adapter invokes a reviewed, version-pinned Codex CLI using `codex exec --json`. Official OpenAI documentation describes `--json` as a JSONL stream containing lifecycle and item events, including possible reasoning, command, file-change, MCP, web-search, and plan items. Therefore the Codex-native stream remains private to the adapter and has conformance fixtures per supported CLI version.

`--output-schema` may constrain a role's final response, but it does not define or validate the complete native event stream. The adapter independently validates both lifecycle and final structured output. It uses explicit sandbox/config settings, a task-scoped working directory, bounded execution, and a sanitized repository-tool environment; local CLI defaults are not accepted as proof of factory isolation.

Provider authentication terminates in an isolated provider-control boundary. A model-invoked repository command must be unable to read the provider credential through environment variables, files, `/proc`, sockets, metadata services, or the provider channel. A successful credential or network probe is a release-blocking failure.

Reference: [OpenAI Codex non-interactive mode](https://developers.openai.com/codex/noninteractive).

## Grok and future adapters

The Grok compatibility adapter implements the same canonical invocation/event contract and declares only capabilities it can prove. It is never an automatic replacement for Codex. Future providers register an operator-reviewed executable, exact supported protocol versions, native version policy, capability set, conformance fixtures, redaction policy, metering semantics, and cancellation behavior.

Changing provider requires a separately recorded decision, a new packet/run, a new budget reservation, and fresh evidence. Lack of a configured or compatible provider ends in a typed failure or `needs_human`.

## Durable control-plane model

PostgreSQL `factory.*` is separate from `trust_ci.*`. The logical model includes:

- immutable accepted intents and packet versions;
- tasks and derived current-state projections;
- runs, typed attempts, lease generations, heartbeats, and deadlines;
- append-only state-transition/audit events;
- capacity allocations and global/per-repository kill switches;
- note, finding, artifact, and terminal-result proposals with idempotency keys;
- usage observations, price-table identity, reservations, reconciliations, and aggregate cost;
- workspace handles and cleanup/reconciliation status.

Secret values and raw provider streams are not database fields. Large safe artifacts are content-addressed outside the database and referenced by digest under bounded retention.

### State semantics through M6

```text
inbox -> triaged -> waiting_design_approval -> queued -> leased
       -> analyzing -> implementing -> verifying -> reviewing
       -> ready_for_human
```

Exceptional states are `retry`, `needs_human`, `dead`, `cancelled`, and `superseded`. `pr_open`, `merged`, and delivery states may be reserved for later schemas but are unreachable while external-write capability is absent.

Provider output never selects a transition. The control plane verifies the expected current state, packet digest, lease fence, allowed terminal type, budget, and idempotency key inside one transaction.

## Leases, retries, concurrency, and budgets

- Claims use `FOR UPDATE SKIP LOCKED`, expiry, heartbeat, and a monotonically increasing fencing token.
- Every note, artifact, usage, and terminal commit checks the current fence. Late output from an expired worker is rejected.
- Global reader allocations cannot exceed 20; allocations for one repository cannot exceed 10; the global application-writer allocation cannot exceed one.
- The writer constraint is a database-enforced singleton fence. One configured writer process is defense in depth, not correctness authority.
- Infrastructure retry count is `0..2` after the initial attempt. Policy, deterministic validation, authentication, unsupported capability/version, budget, security, and provider-quality failures are not relabelled as infrastructure failures.
- Semantic repairs are separate child runs, always assigned to the same fenced writer, with cycles `1..3`. A repeated unresolved finding, risk increase, architecture change, or requested fourth cycle ends in `needs_human`.
- The four-hour wall deadline and USD 25 cost ceiling aggregate across attempts and repairs. Budget is reserved before dispatch and atomically reconciled from trustworthy usage and a versioned price table.
- Missing or invalid usage/pricing blocks another provider call; it never means zero cost. Deadline/budget exhaustion cancels the runtime and records a terminal escalation without deleting evidence.

## Append-only note broker

Readers cannot write application files or shared memory. They submit notes through a broker. Each accepted note contains task/run/author-role identity, lease fence, producer and broker sequence, bounded type and body, provenance/evidence references, source digest, and receive time.

Notes are immutable. Corrections append a new note that references the superseded note; deletion is only a separately governed retention/tombstone event. Note bodies are untrusted assertions, never instructions or state transitions. Consumers independently validate referenced evidence.

The broker rejects oversized content, path/URI abuse, role impersonation, cross-task references, stale fences, duplicate idempotency keys, executable payloads where structured data is required, and note types outside the role contract. It never accepts raw reasoning, scratchpads, unrestricted prompts, or native event streams.

The writer receives a bounded, deterministic note snapshot selected by typed relevance/provenance rules. Notes do not become active governance; M3 controls candidate review and promotion.

## Workspace and Git isolation

Every run gets an exact-state task workspace. Readers see an OS-enforced read-only repository view plus broker-only note append. The writer sees only the currently fenced application workspace and allowlisted paths.

A Git worktree directory is not a security boundary because its `.git` indirection normally reaches a shared common Git directory. The trusted workspace manager therefore owns the common repository and brokers required Git operations. Agent/provider subprocesses cannot reach shared refs, objects, sockets, hooks, configuration, other worktrees, or control-plane credentials. Symlink, hardlink, mount, path traversal, submodule, alternate object database, and hook/config abuse are validated adversarially.

Application-file writes, control-plane writes, governance/holdout/policy writes, and external writes are distinct capabilities. The sole application writer does not thereby gain any other capability.

## Fixed systemd topology

M5 uses a reviewed fixed topology:

```text
one factory supervisor
up to twenty fixed read/note worker instances
one fixed application-writer worker
fixed local broker/workspace services as required by the approved deployment model
```

Task content cannot create or alter unit names, unit files, commands, users, environment paths, credentials, restart policy, or capability settings. systemd supplies liveness, host hardening, resource ceilings, and restart behavior; PostgreSQL supplies ownership and correctness. A restart reconstructs work only from durable state and immutable packets.

Units run under separate least-privilege identities with hardened filesystems, private temporary state, explicit address families, bounded resources, and no access to Trust CI or human secrets. Installation and activation are later explicit operator actions and are absent from this change.

## No-chain-of-thought and retention policy

Durable storage is allowlist-based. Permitted records are concise result summaries, structured findings, evidence references, content digests, bounded safe diagnostics, artifacts, usage, errors, and provenance. Raw prompts are retained only when an approved input-retention class requires a bounded content envelope; raw repository data remains in the workspace/artifact boundary.

Private reasoning, scratchpads, reasoning-token text, unrestricted self-evaluation, unrestricted native JSONL, and unrestricted stdout/stderr are discarded before persistence. Metrics may record reasoning-token counts when supplied, but never reasoning content. Logs redact by construction and enforce size/retention ceilings.

## Threat model and fail-closed response

| Threat or failure | Required response |
| --- | --- |
| Prompt/repository/note requests more authority or secrets | Treat as data; deny capability change; record a bounded security finding when useful |
| Note impersonates policy, control event, or validator | Reject by schema, role, provenance, and channel authority |
| Packet replay, stale SHA/digest, or late worker | Reject dispatch/commit; supersede or reconcile |
| Adapter emits malformed, unknown, covert-reasoning, duplicate-terminal, or flooding output | Terminate; retain only bounded safe diagnostics; record protocol violation |
| Selected provider is absent or incompatible | Typed failure or `needs_human`; no fallback or downgrade |
| Path traversal, symlink escape, shared-Git mutation, or cross-task access | Broker denies; security-significant attempts terminate and block release |
| Repository subprocess probes credentials or network | OS boundary denies; any successful probe blocks M5 exit |
| Missing usage, dishonest accounting, or event amplification | Stop further dispatch; fail closed on budget accounting |
| Implementer claims acceptance or edits validator evidence | Ignore as non-authoritative; independent evidence only |
| Provider asks to push, open PR, merge, deploy, install systemd, or call a connector | Capability is absent; terminate or escalate without obtaining credentials |

## Observability and audit

Structured records correlate `task_id`, `run_id`, repository, exact SHA, packet/spec/architecture digests, provider/adapter/model versions, lease generation, attempt class, and repair cycle. They do not embed untrusted bodies or secrets.

Minimum metrics include queue depth, active reader/writer leases, per-repository allocations, lease reclaims, attempts by class, dead/needs-human tasks, wall time, provider usage/cost, budget stops, protocol violations, note rejections, workspace cleanup, validator disagreements, repairs, and kill-switch state. Alerts cover stuck leases, fence violations, writer-count violations, cost/deadline exhaustion, protocol floods, credential/network isolation failures, dead tasks, and cleanup failures.

Audit is append-only for intake, packet creation, provider selection, capacity allocation, state transition, note/finding/artifact acceptance, usage reconciliation, cancellation, kill switch, and any later external-action request. It stores actor identity and reason without chain-of-thought.

## Resolved design choices

1. M1 schema evolution uses an explicit new version when semantics or required fields change; v1 is not silently reinterpreted. Dual-version readers exist only for a reviewed compatibility window; unknown future versions fail closed.
2. Criterion status/provenance lives in exact-state evidence envelopes around the canonical spec. The spec states intent; local and Trust CI consumers independently derive coverage and bind their own envelopes to the spec digest.
3. Base/head SHA, policy, architecture, and referenced-contract digests are evidence-envelope bindings rather than mutable intent fields. A partial or stale binding cannot be replayed.
4. Evidence and contract references are canonical repository-relative identifiers with containment, symlink, existence, and selector validation. External evidence is named by approved opaque identity/digest and is never fetched implicitly.
5. Documentation-only exemptions are policy decisions made outside untrusted content, exact-diff/state-bound and expiring; post-diff risk escalation cancels them.
6. Historical packages remain historical evidence. Enforcement uses an explicit adoption boundary and bounded migrations, never bulk history rewriting.
7. Route scope/design approval maps to durable architecture/security review evidence. It is distinct from Trust CI Ed25519 human security approval and from a local delegated operational grant.
8. Failure states are typed as `invalid`, `incomplete`, `stale`, `unsupported`, `budget_exhausted`, `needs_human`, or a narrowly defined retryable infrastructure error. Operator remediation is structured and never executes untrusted text.

## Evidence gates by milestone

| Gate | Required proof before the next gate |
| --- | --- |
| M1 | Complete typed specs; path-safe traceability; exact-state criterion receipts; independent holdout and attestation binding; adoption/exemption tests |
| M2/M3 | Schema-valid architecture and governance/debt models; externally enforced critical fitness rules; reviewed rule promotion and revocation |
| M4 | Real PostgreSQL concurrency, fencing, idempotency, retry/dead-letter, budget, kill-switch, restart, and reconciliation tests |
| M5 | Protocol conformance; Codex/Grok fixtures; one-writer/read ceilings; cross-task/Git isolation; credential and egress adversarial tests; systemd restart/orphan drills |
| M6 | Independent exact-SHA semantic verdicts; contradiction handling; same-writer repairs; hard rejection of a fourth cycle; fresh evidence after repair |
| M7-M9 | Deferred. Require preceding exit evidence, shadow-mode cohorts where specified, and a separate scope/authority decision; no capability exists now |

## Design acceptance gate

The design is ready for user review when the canonical document, durable package, five route-selected analysis reports, typed spec, self-review, and decision entry agree; all placeholders are removed; focused validation is green; and one local design/docs commit exists on `feature/model-agnostic-factory`.

Approval of this design authorizes only a later, separately scoped M1 completion slice. It does not authorize M2-M9, implementation now, external writes, or systemd installation.
