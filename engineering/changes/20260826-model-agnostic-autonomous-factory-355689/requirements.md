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
- [x] AC-012: At the original design gate, the package stopped at `scope_and_design_approval`; later implementation authority is recorded separately below and still implies no external action.

## Approved implementation acceptance criteria

- [ ] AC-013: M3 strict schemas and bounded loader make rule, debt, and canonical-example records machine-readable, canonical, path-safe, versioned, and digest-bound.
- [ ] AC-014: Agent output can create only candidate rules; independent review plus explicit human governance approval is required for activation, and expired/deprecated/revoked rules are ineffective.
- [ ] AC-015: M3 detects conflicting/duplicate patterns, enforces intentional-debt ownership/triggers/tests, keeps Markdown non-authoritative, and publishes the exact six-field `GovernanceHandoffV1` specified by the M3 plan.
- [ ] AC-016: M2 executable architecture models M3/M4 boundaries without weakening M1/M2 evidence or changing `trust-ci/**`.
- [ ] AC-017: M4 accepts only valid immutable M1/M2/M3 handoffs, deduplicates identical intake, and supersedes stale source/base/spec/architecture/governance/policy variants.
- [ ] AC-018: Real PostgreSQL tests prove SKIP LOCKED ownership, monotonic fencing, late-result rejection, lease reclaim, initial-plus-two retries, dead-letter, and restart-safe reconciliation.
- [ ] AC-019: PostgreSQL enforces at most 20 global readers, 10 readers per repository, and one global application writer, plus four-hour/USD-25 aggregate ceilings.
- [ ] AC-020: Global/repository kill switches stop new claims without deleting evidence, and every transition/actor is append-only audited.
- [ ] AC-021: M4 exposes authenticated versioned Unix-socket submit/status/list/cancel/health operations with idempotency/correlation and a least-privilege admin-client scope suitable for a later `baby-bot` adapter.
- [ ] AC-022: No factory endpoint or credential enables provider execution, systemd activation, GitHub/external write, Trust CI state access, or production mutation.
- [ ] AC-023: Bot integration is blocked until a human rotates the exposed Telegram token outside the agent and the later bot slice proves admin allowlisting plus request-URL redaction/log-level guards.

## Failure and edge cases

- Missing or incompatible provider becomes a typed failure or `needs_human`, never fallback.
- Stale packet/SHA/digest or late fence rejects the result.
- Missing trustworthy cost/usage prevents another provider call; it is not zero cost.
- Unknown, malformed, oversized, reasoning-bearing, or ambiguous adapter output fails closed.
- Path/symlink/shared-Git escape, credential probe, or network escape is a release-blocking isolation failure.
- A fourth repair cycle, repeated unresolved finding, architecture change, or risk increase requires a human.
- Duplicate intake returns the existing task; a conflicting reuse of an idempotency key fails.
- An expired fence, killed worker, budget/accounting gap, active kill switch, or stale M1/M2/M3 digest blocks dispatch/commit.
- The `baby-bot` network namespace cannot reach host loopback, so the integration contract uses an operator-owned Unix socket with scoped bearer authentication and never a token in a URL.

## Non-functional requirements

- Security: least capability, untrusted-data labelling, credential/network isolation, no self-approval, no external-write capability, and independent Trust CI.
- Reliability: PostgreSQL source of truth, idempotency, leases/fences, heartbeat/expiry, reconciliation, typed retries, kill switches, and append-only audit.
- Performance: bounded concurrency, wall time, cost, tokens, events, output, notes, artifacts, logs, queues, and retention.
- Observability: task/run/SHA/digest/provider/lease correlation, usage/cost, protocol violations, budget stops, isolation failures, repairs, and kill-switch state without secrets or reasoning content.
