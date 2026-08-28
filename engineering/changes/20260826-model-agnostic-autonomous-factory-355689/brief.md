# Model Agnostic Autonomous Factory

Change ID: `20260826-model-agnostic-autonomous-factory-355689`
Created: 2026-08-26T02:06:07+00:00
Risk: high
Complexity: high-risk
Domains: ai, security

## Problem

The repository has an approved provider-neutral design and an exact M2-A implementation at `635c9ddf2d63c1ea823074106976a8f3de6299a9`, but it still lacks controlled machine-readable governance (M3) and the durable PostgreSQL factory control plane (M4).

## Outcome

Deliver two reviewable stacked implementation PRs: M3 controlled knowledge/debt on exact M2, followed by M4 durable intake/scheduling/fencing/capacity/recovery consuming frozen M1/M2/M3 digests. The M4 API also freezes an authenticated Unix-socket submit/status/list/cancel/health contract for a later admin-only `/home/pall/baby-bot` integration.

## Scope

### In scope

- Provider-neutral control-plane and adapter boundaries.
- PostgreSQL durability, fencing, concurrency, retry, deadline, and cost invariants.
- Codex-first and Grok-compatibility adapter semantics through a versioned JSON/JSONL contract.
- Fixed systemd topology, isolated worktrees, tool/credential/network isolation, and append-only notes.
- M1-M6 dependency gates and evidence requirements; M7-M9 remain deferred.
- Five route-selected analysis reports, typed package completion, design self-review, and one local docs commit.
- Exact M2-A as the immutable stacked base; no reimplementation or modification of Trust CI.
- M3 rule/debt/canonical-example lifecycle and exact `GovernanceHandoffV1`.
- M4 separate `factory/` package, PostgreSQL migrations/store, intake/idempotency, leases/fencing/reclaim/retry/dead, 20/10/1 capacity, budgets, kill switches, audit, reconciliation, and local API/CLI.
- Versioned Unix-domain-socket factory API for a later admin-only `baby-bot` adapter.

### Out of scope

- Reopening or rewriting the already reviewed M2-A implementation.
- A second change package or any `grok_change.py start` invocation.
- Provider execution, systemd units, installation/activation, or deployment.
- Push, PR, merge, release, connector call, production mutation, or any external write.
- Provider adapters, isolated workspaces, note execution broker, systemd installation/activation, and external-write behavior (M5+).
- Editing, restarting, or deploying `/home/pall/baby-bot`; that is a separate integration slice after M4 API review.
- M7-M9 behavior.

## Constraints

- Backward compatibility: existing M1 v1 and historical packages are not silently reinterpreted; future schema changes use explicit versions and an adoption boundary.
- Data/privacy: prompt, repository, notes, logs, and provider output are untrusted; secrets and chain-of-thought are excluded from durable artifacts.
- Performance: readers are capped at 20 globally and 10 per repository; one global application writer; aggregate task wall time is four hours and cost is USD 25.
- Operational: no silent provider fallback, no autonomous external writes, fixed systemd processes only after a later operator gate, and Trust CI remains separate merge authority.

## Scope expansion authority

After the original design gate, the user explicitly approved full stacked M2 -> M3 -> M4 implementation without functional cuts and asked to reduce only redundant repeated tests. The user also required the existing `baby-bot.service`, isolated in `/run/netns/vpn`, to consume the future factory through a Unix-domain-socket admin API; only that M4 contract is in this scope, while bot code/deployment and Telegram-token rotation remain separate human/operator-controlled work.
