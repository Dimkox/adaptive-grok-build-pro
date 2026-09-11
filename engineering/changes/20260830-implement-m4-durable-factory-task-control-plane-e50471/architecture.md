# Architecture — M4 Durable Factory Task Control Plane

## Current behavior

The routed checkout contains M1 but no `factory/`, M2 architecture handoff, or M3 governance handoff. Reviewed M2 and M3 exist as stacked PRs, but their App-owned checks are awaiting exact-SHA human approval scopes.

## Proposed behavior

```text
frozen M1 + M2 + M3 handoffs
  -> authenticated local intake over Unix socket
  -> factory service transactions
  -> PostgreSQL factory.* operational truth
  -> bounded scheduler / lease / reconciliation commands
  -> ready_for_human
```

M4 stops at the source-level local control plane. M5 owns execution workspaces and providers; M7 owns GitHub delivery; Trust CI independently owns exact-SHA verification and merge authority.

## Components and boundaries

- `factory/contracts.py`: closed canonical input/handoff/limit contracts and digests.
- `factory/state.py`: exhaustive deterministic transition and retry policy.
- `factory/migrations.py` and packaged SQL: immutable factory-only schema history.
- `factory/store.py`: all locking, fencing, capacity, budget, audit, and reconciliation transactions.
- `factory/service.py`: typed use cases with no shell/provider/external capability.
- `factory/api.py` and `cli.py`: thin scoped local boundaries with bounded projections.
- PostgreSQL `factory.*`: sole authority for accepted intent and operational state; separate roles/search path/backups from Trust CI.

## Data and concurrency model

Immutable accepted intents feed mutable task projections, immutable runs/attempts, monotonic lease fences, capacity allocations, budget reservations/usage, kill switches, reconciliation runs, task events, and append-only audit. Claim locks eligible work with `FOR UPDATE SKIP LOCKED`, locks capacity in stable global/repository order, increments a durable fence, and creates the allocation in one transaction. Every heartbeat/proposal/release binds task, run, owner, fence, packet digest, state, live expiry, deadline, budget, and idempotency key.

## API and compatibility

The versioned public/admin contract contains health plus task submit/show/list/cancel over an operator-owned Unix socket. Worker/operator claim, heartbeat, proposal, kill, and reconcile operations use separate scopes. A future `baby-bot` client may receive only submit/read/list/cancel; M4 never reads Telegram credentials or edits/deploys the bot.

## Decisions

- Implement the existing approved M4 plan, not a new alternative.
- Stack only on the exact M3 head accepted by external Trust CI; routed base `1c062998` is rejected for implementation.
- Prefer a separate factory database; if one PostgreSQL cluster is used, explicit `factory` schema, role search paths, grants, migration registry, backup, and restore ownership are mandatory.
- Kill switches block new claims and preserve evidence; no forced deletion.
- `ready_for_human` is M4's positive terminal state; PR/merge/deploy states remain rejected future values.

## Risks and mitigations

- Wrong base or substitute handoff: exact accepted M3 SHA and cross-handoff digest/SHA validation.
- Zombie worker: database time, monotonic fences, and late-result integration tests.
- Capacity/budget race: stable lock order and atomic reservation/allocation transactions.
- Audit loss: insert-only runtime grants, hash chaining, and no cascading task deletion.
- Trust collapse: no Trust CI imports, queries, roles, credentials, keys, checks, or authority edges.
- API/token exposure: no-follow `0600` token files, scoped constant-time auth, `0660` socket, strict bounds and redaction.
- Migration failure: advisory lock, immutable checksums, disposable rehearsal, kill/stop, backup, separate restore, and forward fix.

## Prerequisite gate

Implementation waits for PR #10 and PR #11 to pass their App-owned exact-head checks and for a route regenerated on that accepted M3 head. No code is permitted on the divergent routed base.
