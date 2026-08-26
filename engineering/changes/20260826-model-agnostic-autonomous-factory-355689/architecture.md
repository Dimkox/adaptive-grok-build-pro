# Architecture — Model Agnostic Autonomous Factory

## Current behavior

M0 Trust CI is live and separate. M1 has a strict schema/parser/CLI/test foundation, but criterion-aware local receipts, external holdout enforcement, signed attestation binding, and complete adoption/staleness rules are not yet evidenced. M2-M6 runtime surfaces do not exist.

## Proposed behavior

The canonical design is `docs/superpowers/specs/2026-08-26-model-agnostic-autonomous-factory-design.md`. A deterministic provider-neutral factory consumes stable M1-M3 digests, persists tasks and leases in PostgreSQL `factory.*`, dispatches fixed systemd workers into isolated task workspaces, normalizes provider-native output through versioned adapters, and stops with a local human-review bundle through M6.

## Components and boundaries

- Intent plane: typed spec, executable architecture, reviewed governance/debt.
- Control plane: API, supervisor/scheduler, PostgreSQL tasks/runs/fences/budgets/audit.
- Execution plane: packet builder, workspace/tool broker, provider adapters, note broker, at most 20 readers and one writer.
- Semantic plane: independent validators and at most three same-writer repair cycles.
- Trust plane: independent Trust CI exact-SHA App-owned verdict and human-owned delivery.

Provider adapters translate only. They cannot access the database, select fallback, change policy, approve work, or perform external writes. Git common state, credentials, and network are brokered outside untrusted processes; a worktree directory alone is not treated as isolation.

## Data flow

```text
approved M1-M3 records -> immutable packet -> fenced worker
worker -> provider adapter -> validated canonical events
events -> note/artifact/usage proposals -> transactional control-plane decision
local result -> independent semantic review -> ready_for_human
ready_for_human -> separate Trust CI/human delivery process, not factory authority
```

## API and event contracts

- Factory adapter invocation: one bounded canonical JSON object on stdin.
- Factory adapter events: bounded allowlisted JSONL with identity, version, sequence, usage, structured proposals, and exactly one terminal event.
- Codex native `--json` and Grok native output remain private to their adapters.
- Unknown protocol/capability, malformed output, missing trustworthy usage, and incompatible provider fail closed.
- Protocol, adapter, provider, native runtime, and model versions are distinct fields.

## Repository impact

This gate changes documentation and the durable package only. It does not add `factory/`, database state, dependencies, root packaging markers, GitHub Actions, systemd units, or runtime behavior.

## Decisions

- M1 is an incomplete integration milestone, not greenfield and not complete merely because commit `48cb973` exists.
- Evidence status/provenance lives in exact-state envelopes around canonical intent.
- Provider selection is explicit and immutable per run; switching provider creates a new run and never occurs silently.
- Notes are immutable untrusted assertions and cannot become control events or active governance.
- systemd provides liveness; PostgreSQL leases/fences provide correctness.
- Through M6 external-write states are unreachable.

## Risks and mitigations

- Prompt injection: treat all content as data and enforce capability outside the model; do not claim prevention.
- Credential exfiltration: separate provider-control identity/channel and adversarially prove repo subprocess isolation.
- Cross-task/Git mutation: broker common Git operations and enforce OS-level mounts/namespaces.
- Provider coupling: normalize native streams behind a conformance-tested versioned protocol.
- Late/duplicate work: idempotency plus generation fencing on every durable proposal.
- Cost/runaway loops: pre-reservation and aggregate hard limits with fail-closed missing usage.
- Trust collapse: keep `factory.*`, credentials, authority, and verdicts separate from `trust_ci.*`.
