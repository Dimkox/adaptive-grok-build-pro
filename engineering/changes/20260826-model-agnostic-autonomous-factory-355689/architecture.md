# Architecture — Model Agnostic Autonomous Factory

## Current behavior

M0 Trust CI remains separate. M1 is the typed-intent authority. Exact M2-A exists at `635c9ddf2d63c1ea823074106976a8f3de6299a9`; M3 and `factory/` do not yet exist on this branch.

## Proposed behavior

The canonical design remains `docs/superpowers/specs/2026-08-26-model-agnostic-autonomous-factory-design.md`. The approved implementation is split into two stacked PRs: M3 publishes reviewed governance/debt/example digests and `GovernanceHandoffV1`; M4 consumes frozen M1/M2/M3 bindings and owns PostgreSQL `factory.*`, intake, scheduling, fencing, limits, kill switches, audit, and reconciliation. Provider/workspace/systemd execution remains M5.

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

This planning commit changes documentation and the durable package only. The approved M3 implementation adds governance source; the stacked M4 implementation adds the isolated `factory/` package and migrations, but neither adds a root packaging marker, GitHub Actions, provider execution, systemd activation, or external writes.

## Decisions

- M1 is an incomplete integration milestone, not greenfield and not complete merely because commit `48cb973` exists.
- Evidence status/provenance lives in exact-state envelopes around canonical intent.
- Provider selection is explicit and immutable per run; switching provider creates a new run and never occurs silently.
- Notes are immutable untrusted assertions and cannot become control events or active governance.
- systemd provides liveness; PostgreSQL leases/fences provide correctness.
- Through M6 external-write states are unreachable.
- The M4 client boundary is authenticated HTTP over an operator-owned Unix socket so a later admin-only `baby-bot.service` adapter can cross its separate VPN network namespace without exposing TCP.
- The bot adapter, Telegram admin mapping, service changes, deployment, and token rotation are a separate post-M4 slice.

## Risks and mitigations

- Prompt injection: treat all content as data and enforce capability outside the model; do not claim prevention.
- Credential exfiltration: separate provider-control identity/channel and adversarially prove repo subprocess isolation.
- Cross-task/Git mutation: broker common Git operations and enforce OS-level mounts/namespaces.
- Provider coupling: normalize native streams behind a conformance-tested versioned protocol.
- Late/duplicate work: idempotency plus generation fencing on every durable proposal.
- Cost/runaway loops: pre-reservation and aggregate hard limits with fail-closed missing usage.
- Trust collapse: keep `factory.*`, credentials, authority, and verdicts separate from `trust_ci.*`.
