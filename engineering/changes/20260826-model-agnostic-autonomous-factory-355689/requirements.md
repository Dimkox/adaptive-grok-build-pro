# Requirements — Model Agnostic Autonomous Factory

## Acceptance criteria

- [x] AC-001: A canonical design document fixes provider-neutral planes, components, trust boundaries, state ownership, and mandatory M1-M6 sequencing.
- [x] AC-002: The design records readers `<=20`, readers per repository `<=10`, writers `=1`, infrastructure retries `<=2`, repairs `<=3`, wall time `<=4h`, and cost `<=USD 25` as hard ceilings.
- [x] AC-003: Codex `exec --json`, Grok compatibility, and future providers sit behind an explicit versioned JSON-in/JSONL-out protocol with no silent fallback.
- [x] AC-004: Prompt, repository, notes, native events, and model results are untrusted; controls are enforced outside the model without claiming prompt-injection prevention.
- [x] AC-005: Repository subprocesses receive no credentials and no network; raw reasoning and unrestricted provider streams do not enter durable storage.
- [x] AC-006: PostgreSQL fencing enforces one writer, reader ceilings, late-result rejection, bounded retries, budgets, kill switches, and restart recovery separately from `trust_ci.*`.
- [x] AC-007: Fixed systemd topology, isolated workspaces, brokered Git, append-only notes, and the distinction between worktrees and security isolation are specified.
- [x] AC-008: M7-M9 and all autonomous external-write behavior remain unreachable pending evidence and a separate future approval.
- [x] AC-009: The active typed spec is red-risk, evidence-mapped, schema-valid, and placeholder-free.
- [x] AC-010: All five route-selected read-only analysis reports are present and synthesized.
- [x] AC-011: Self-review checks placeholders, contradictions, security boundaries, and scope leakage.
- [x] AC-012: The package stops at `scope_and_design_approval`; no implementation or external action is implied.

## Failure and edge cases

- Missing or incompatible provider becomes a typed failure or `needs_human`, never fallback.
- Stale packet/SHA/digest or late fence rejects the result.
- Missing trustworthy cost/usage prevents another provider call; it is not zero cost.
- Unknown, malformed, oversized, reasoning-bearing, or ambiguous adapter output fails closed.
- Path/symlink/shared-Git escape, credential probe, or network escape is a release-blocking isolation failure.
- A fourth repair cycle, repeated unresolved finding, architecture change, or risk increase requires a human.

## Non-functional requirements

- Security: least capability, untrusted-data labelling, credential/network isolation, no self-approval, no external-write capability, and independent Trust CI.
- Reliability: PostgreSQL source of truth, idempotency, leases/fences, heartbeat/expiry, reconciliation, typed retries, kill switches, and append-only audit.
- Performance: bounded concurrency, wall time, cost, tokens, events, output, notes, artifacts, logs, queues, and retention.
- Observability: task/run/SHA/digest/provider/lease correlation, usage/cost, protocol violations, budget stops, isolation failures, repairs, and kill-switch state without secrets or reasoning content.
