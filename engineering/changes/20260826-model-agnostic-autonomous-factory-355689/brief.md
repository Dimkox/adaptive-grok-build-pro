# Model Agnostic Autonomous Factory

Change ID: `20260826-model-agnostic-autonomous-factory-355689`
Created: 2026-08-26T02:06:07+00:00
Risk: high
Complexity: high-risk
Domains: ai, security

## Problem

The repository has a partial M1 typed-intent foundation and a roadmap for a durable software factory, but it lacks one approved provider-neutral design that fixes trust boundaries, interfaces, limits, milestone dependencies, and the no-external-write boundary before implementation.

## Outcome

A reviewable, internally consistent architecture specification and durable typed package define the factory without implementing it. The artifacts give the user a concrete scope/design gate and make M1 completion the next permitted milestone.

## Scope

### In scope

- Provider-neutral control-plane and adapter boundaries.
- PostgreSQL durability, fencing, concurrency, retry, deadline, and cost invariants.
- Codex-first and Grok-compatibility adapter semantics through a versioned JSON/JSONL contract.
- Fixed systemd topology, isolated worktrees, tool/credential/network isolation, and append-only notes.
- M1-M6 dependency gates and evidence requirements; M7-M9 remain deferred.
- Five route-selected analysis reports, typed package completion, design self-review, and one local docs commit.

### Out of scope

- Implementation code or an implementation plan.
- A second change package or any `grok_change.py start` invocation.
- Provider execution, migrations, `factory/`, systemd units, installation, or deployment.
- Push, PR, merge, release, connector call, production mutation, or any external write.
- M7-M9 behavior.

## Constraints

- Backward compatibility: existing M1 v1 and historical packages are not silently reinterpreted; future schema changes use explicit versions and an adoption boundary.
- Data/privacy: prompt, repository, notes, logs, and provider output are untrusted; secrets and chain-of-thought are excluded from durable artifacts.
- Performance: readers are capped at 20 globally and 10 per repository; one global application writer; aggregate task wall time is four hours and cost is USD 25.
- Operational: no silent provider fallback, no autonomous external writes, fixed systemd processes only after a later operator gate, and Trust CI remains separate merge authority.
