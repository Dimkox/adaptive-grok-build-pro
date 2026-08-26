# AI/security analysis — provider-neutral factory

Route: `35568941ae59`
Change: `20260826-model-agnostic-autonomous-factory-355689`
Role: read-only `ai_architect`

## Verdict

The approved architecture is safe only if the provider-neutral control plane, rather than any model, prompt, repository file, note, provider adapter, or native JSON stream, owns task state, capabilities, limits, and provider selection. `codex exec --json` and the Grok compatibility interface are provider-native transports behind a validated adapter boundary; neither is the factory protocol or durable evidence by itself.

These properties must be frozen as typed M1 invariants and forbidden outcomes, then consumed by M2/M3. Enforcement belongs to M4–M6 in the mandatory order; this report does not imply those milestones exist or authorize implementation.

## Trust boundaries and assets

| Boundary | Trusted responsibility | Untrusted input / prohibited authority |
| --- | --- | --- |
| Approved intent plane | Schema-valid spec, stable requirement IDs, architecture/policy digests, human design gate | Raw prompt and route inference cannot grant tools, credentials, budgets, or external actions |
| PostgreSQL `factory.*` control plane | State transitions, leases/fences, provider selection, budgets, idempotency, audit | Provider/model output cannot update state directly; must remain separate from `trust_ci.*` |
| Immutable packet builder | Canonical packet bytes and digest from approved durable fields | Repository text and notes are labelled content, never system/control instructions |
| Provider adapter | Translate one canonical invocation and normalize native output | No scheduler/database authority, policy decisions, fallback, Trust CI material, or external-write credentials |
| Workspace/tool broker | Exact task workspace, role/path/tool enforcement, sanitized repo subprocesses | A Git worktree alone is not isolation; shared Git metadata and other workspaces remain inaccessible |
| Note broker | Append-only validated facts/findings with provenance and bounds | Notes cannot mutate policy, packet, role, tool grants, provider, budget, lease, or task state |
| Semantic validators | Read-only structured verdicts against exact SHA and typed criteria | No writer capability, implementer self-evaluation, or implementer chain-of-thought |
| Trust CI | Independent exact-SHA verification and authoritative App-owned check | Factory cannot sign/publish its verdict or access its keys, holdout, policy, or approval trust store |

Protected assets are repository integrity, one-writer exclusivity, approved intent, task/provider budgets, tenant/task isolation, provider credentials, Trust CI and human approval material, structured evidence, and audit provenance.

## Immutable task-packet semantics

- A packet is produced only from approved durable records and canonical serialization; its schema version and digest cover every control field. Workers verify the digest before execution. A changed prompt, spec, architecture digest, base SHA, role, capability, provider, model, limit, or policy creates a new packet/run and supersedes the old one; packets are never edited in place.
- Required control fields include task/run identity, exact base SHA, spec and architecture digests, selected role, explicit provider/adapter/model identity, protocol version, allowed paths/tools/network destinations, criterion IDs, reasoning effort, output contract, and hard runtime/token/cost ceilings.
- Raw prompt, repository content, retrieved text, logs, and notes enter a separately labelled content envelope with origin, digest, size, and retention metadata. They are quoted/delimited as data and cannot override system policy, request more authority, select a provider, or reinterpret acceptance criteria.
- Repair starts a fresh context and a new child packet bound to the new exact SHA and prior structured findings. It does not append an endless transcript or reuse mutable chat memory.
- Packets contain no database credentials, Trust CI/human/production secrets, external-write capability, or hidden reasoning. Evidence references are opaque validated references, never commands, URLs to fetch implicitly, or filesystem paths resolved outside an allowlisted repository root.

## Versioned Codex/Grok adapter protocol

The canonical boundary should be one bounded JSON invocation on stdin and bounded JSONL events on stdout from an operator-configured executable. Stderr is a bounded, redacted diagnostic channel, not protocol or evidence. Each event carries protocol/schema version, task/run identity, monotonically increasing sequence, type, and bounded payload; trusted receive time and durable ordering are added by the broker.

Allowlisted event classes are capability/identity handshake, lifecycle, concise note/finding, artifact reference, usage, and exactly one terminal result/error. Protocol major/schema compatibility is exact and explicit; adapter, provider, model, and native-format versions are separate recorded fields. Malformed/oversized JSON, unknown required fields or event types, identity/version mismatch, non-monotonic sequence, undeclared capability, duplicate/missing terminal result, invalid artifact reference, or unexpected stdout fails closed.

Provider selection is persisted before dispatch. An unavailable, incompatible, or capability-incomplete provider yields a typed failure or `needs_human`; the adapter never selects a replacement. Switching provider, if later explicitly authorized, requires a new run/packet, recorded reason, new budget reservation, and fresh evidence. There is no silent Codex-to-Grok or Grok-to-Codex fallback.

Native Codex/Grok streams are not retained as canonical evidence. The adapter persists only allowlisted conclusions, evidence references, findings, artifacts, usage, and terminal status after validation and redaction.

## Notes and no-chain-of-thought rule

Notes are append-only, task/run/author-role scoped, broker-sequenced, size-limited, provenance-tagged records containing a concise conclusion or finding plus evidence references. Readers may submit them only through the broker; they cannot write shared files or another task's notes. Consumers treat note bodies as untrusted assertions and independently verify evidence.

Durable storage uses an allowlist, not redaction after broad logging. It must not store raw prompts beyond the approved retained input envelope, scratchpads, reasoning tokens, hidden reasoning, self-evaluation transcripts, unrestricted native provider JSONL, or unrestricted stdout/stderr. Reasoning/scratchpad event types are discarded before the durable boundary; if an adapter cannot separate them reliably, it is ineligible. Operational records may contain only concise result summaries, structured findings, usage, errors, digests, and provenance.

## Credentials, network, and external-action isolation

- Repository commands execute with a sanitized environment, no inherited provider/factory/Trust CI/human/production credentials, no credential files, and no readable parent-process secrets. Secret values never enter packets, notes, manifests, artifacts, command lines, or logs.
- Provider authentication terminates in a separately isolated provider-control boundary. Provider egress is distinct from repo-tool execution: repo subprocesses have no network by default, while only the provider transport receives an explicit destination allowlist. A Codex adapter is not compliant until adversarial tests prove a model-invoked repo command cannot enumerate/read provider credentials or use the provider channel for arbitrary egress; inability to prove this fails closed rather than weakening the invariant.
- Readers get an OS-enforced read-only repository view and broker-only note append. The sole application writer gets only its fenced task workspace and allowlisted paths. The trusted workspace manager brokers Git operations so shared `.git` state, refs, sockets, symlinks, and other worktrees are not reachable.
- Through M6, allowed effects are local task-workspace changes and bounded evidence only. Push, PR, merge, release, deploy, systemd installation, production mutation, connectors, and other external writes are absent capabilities, not prompt prohibitions.

## Bounded execution semantics

- Scheduler ceilings are readers `<=20` globally, readers `<=10` per repository, and exactly one application writer, enforced transactionally by leases/fencing rather than process counts or prompts.
- Infrastructure retry count is `0..2` after the initial attempt. Deterministic validation, policy, authentication, unsupported capability/version, budget, and prompt-injection failures are not retryable infrastructure failures.
- Semantic repair cycles are independently capped at `3`, always returned to the same fenced writer. A fourth cycle, repeated finding, risk increase, or architecture change ends in `needs_human`.
- The four-hour wall deadline and USD 25 task cost ceiling are aggregate across attempts and repair cycles. Budget is reserved before dispatch and reconciled from trustworthy usage. Missing/invalid usage or pricing blocks further calls; it never means zero cost. Token, event, line, note, artifact, log, and queue sizes also require hard ceilings.
- Lease generation/fencing is checked on every note, artifact, usage, and terminal commit. Late output from an expired worker is rejected. Restart recovery derives only from PostgreSQL durable state.

## Abuse cases and fail-closed requirements

| Abuse/failure | Required response |
| --- | --- |
| README/prompt/note says to ignore policy, expose secrets, or grant tools | Treat as data; emit a structured security finding if relevant; never change capabilities |
| Malicious note impersonates a control event or validator | Reject by schema/role/provenance; note channel cannot perform state transitions |
| Packet replay, stale SHA/digest, or late fenced worker | Reject commit/dispatch; mark stale/superseded or reconcile, without retrying as fresh work |
| Adapter emits unknown events, covert scratchpad, multiple terminal results, or log flood | Stop/kill run, retain only bounded safe diagnostics, classify protocol violation |
| Provider unavailable or lacks usage/isolation/structured-output capability | Typed terminal failure or `needs_human`; no fallback or capability downgrade |
| Model attempts path traversal, symlink escape, shared-Git mutation, cross-task read, or network access | Tool broker denies; terminate on repeated/security-significant attempt; preserve structured audit evidence |
| Repo subprocess tries environment, `/proc`, credential files, sockets, metadata endpoints, or DNS exfiltration | OS/network boundary denies; any successful probe is a release-blocking isolation failure |
| Cost/token/event amplification or dishonest/missing usage | Reservation and aggregate ceilings stop dispatch; missing trustworthy accounting fails closed |
| Implementer claims acceptance, edits findings, or submits its own approval | Ignore as non-authoritative; independent validator/control-plane records only |
| Prompt/provider asks to push, open PR, merge, deploy, install systemd, or call a connector | Capability absent; terminate/escalate if attempted; never translate request into external credentials |

## M1 design requirements for downstream safety

M1 must assign stable IDs to the trust invariants and forbidden outcomes above, make the high-risk spec complete and placeholder-free, and bind evidence to the canonical spec digest and exact repository state. M2 must model the trust/data/network edges; M3 must ensure notes cannot promote themselves into policy. Only then may M4 enforce durable state/limits, M5 enforce execution/adapters/isolation, and M6 enforce independent semantic repair. M7–M9 remain unavailable until their evidence and a separate authorization exist.

The current named `scope_and_design_approval` gate is fail closed: absent approval is not a provider failure, retry condition, or permission to implement.
