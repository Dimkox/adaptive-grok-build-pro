# Architecture — M4 Durable Factory Task Control Plane

## Boundary and data flow

```text
frozen M1 + M2 + M3 + M0 evidence
  -> authenticated bounded Unix-socket request
  -> pure factory contracts/state/service
  -> PostgreSQL factory.* transaction
  -> immutable intent/run/attempt/event/audit plus task projection
  -> bounded scheduler/reconciler
  -> ready_for_human
```

`factory/` is a nested local Python package. `contracts.py` owns closed immutable records and canonical digests; `state.py` owns pure transitions/retry decisions; `migrations.py` and packaged SQL own the factory-only schema; `store.py` owns SQL/transactions; `service.py` owns use cases; `api.py` and `cli.py` are thin local adapters. There is deliberately no outbox because M4 has no external publication.

## Integrity and concurrency

Intake locks a stable source identity, returns exact duplicates and supersedes changed nonterminal generations atomically. Claim uses database time, `FOR UPDATE SKIP LOCKED`, stable global/repository capacity locks, a strictly increasing task fence and one transaction for run/attempt/allocation/event/audit. Every worker mutation binds task, run, owner, fence, packet digest, state, live lease, deadline, budget and command idempotency.

PostgreSQL `factory.*` is the only M4 operational authority. Its migrations, registry, roles, credentials and search path are independent of Trust CI. Migrations are contiguous/checksum-locked under an advisory lock and forward-only after durable intake. Audit is insert-only and hash chained. Reconciliation performs ordered keyset work, max 100 rows, with a 5-second transaction-local timeout.

## API, security and compatibility

The versioned API runs over an operator-owned Unix socket. Bearer tokens come from no-follow regular `0600` files, compare constant-time, map to closed scopes and are never logged. Socket mode is `0660`; bodies are at most 1 MiB; pages and projections are bounded. The CLI only calls the API. TCP, provider/Git/GitHub/deploy/systemd/external-write operations are absent.

M2/M3 producer handoffs keep their producer exact-base/head pairs. M4 validates closed shapes and cross-digest/SHA compatibility; it never invents those values from the current implementation commit. A fresh M0 observation (<=300 seconds) or named issuer/scope/expiry-bounded bootstrap exception is required at intake.

## Failure, rollout and recovery

Only database unavailable, worker lost, provider transport unavailable and temporary resource exhaustion are retryable; attempt three ends dead. Missing accounting blocks work. Kill switches block new claims while existing leases end cooperatively or expire. Source rollout is local/disposable only. Recovery is global kill, stop local intake/claims, preserve state/audit, restore a backup into a separate database for comparison, and forward-fix with migration `008+`.
