# M4 Durable Factory Task Control Plane

Change ID: `20260830-implement-m4-durable-factory-task-control-plane-e50471`
Route: `e50471553166`
Risk: high
Complexity: high-risk
Domains: data, API, security

## Problem

The repository has typed intent and reviewed stacked M2/M3 implementations, but no durable factory control plane. Work cannot yet be accepted, deduplicated, scheduled, fenced, budgeted, killed, audited, or recovered independently of an interactive agent session.

## Outcome

Add a separate `factory/` Python service backed by PostgreSQL `factory.*`. Authenticated local callers can submit immutable M1/M2/M3-bound task intake, inspect and cancel tasks, while workers use fenced leases and the scheduler enforces bounded capacity, retries, budgets, kill switches, append-only audit, and restart-safe reconciliation.

## Scope

### In scope

- Closed immutable task, run, attempt, handoff, limit, actor, failure, and lease contracts.
- Factory-only PostgreSQL migrations, transactions, indexes, constraints, roles, and recovery.
- Idempotent intake, stale-generation supersession, `FOR UPDATE SKIP LOCKED` claims, monotonic fencing, heartbeats, reclaim, initial attempt plus two infrastructure retries, and dead-letter state.
- Database-enforced capacity ceilings: 20 global readers, 10 readers per repository, and one live application writer.
- Four-hour, USD 25, token, output, event, and repair-capacity ceilings with fail-closed accounting.
- Global/repository kill switches, append-only hash-chained audit, and bounded idempotent reconciliation.
- Scoped local Unix-socket API and matching CLI; public/admin operations are health, submit, show, list, and cancel.
- Real disposable PostgreSQL concurrency and restart tests, architecture/tooling integration, README, rollout, rollback, verification, and independent reviews.

### Out of scope

- Provider/model execution, repository commands, workspaces, systemd activation, GitHub fetch/push/PR/merge, release, deployment, connectors, Trust CI publication, or production mutation.
- Reuse of `trust_ci.*`, Trust CI roles, credentials, signing keys, approvals, holdout, or GitHub App authority.
- Editing or deploying `/home/pall/baby-bot`; Telegram token rotation and bot authorization are a later operator-owned slice.
- M5 through M9 behavior.

## Constraints

- M4 must stack on the exact externally accepted M3 head and consume its frozen M1/M2/M3 interfaces; it must not recreate substitutes.
- The routed base `1c06299894279a88b881defa3f19b004fa742223` lacks M2/M3 and diverges from M3 head `d4cc01fe8d6ec82cce93106191774fc32e8dbb46`; it is not an implementation base.
- PR #10 currently lacks exact-SHA `governance` approval. PR #11 currently lacks exact-SHA `database` and `governance` approvals. The App-owned checks are `ACTION_REQUIRED`, so implementation is paused at the prerequisite human trust gate.
- M0 availability must be observed fresh at intake or a named, bounded bootstrap exception must be recorded; no implicit waiver is allowed.
- No root packaging marker or GitHub Actions may be added. Existing unrelated working-tree changes must be preserved.

## Scope ruling

The previously approved design and implementation plan remain authoritative. After PRs #10 and #11 pass their exact-head Trust CI gates, create the isolated M4 branch/worktree from that accepted M3 head, refresh the route/base fingerprint there, and dispatch only `data_implementer` as the product write owner.
