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

The authenticated metrics surface has three fixed families and no caller-controlled labels. Queue/state, transitions, leases, capacity, budget, kills and reconciliation/repair come from one fixed-row PostgreSQL snapshot maintained transactionally with authoritative writes and read under fixed 5-second statement and 500-millisecond lock timeouts. Runtime has neither table DML nor generic-key capabilities: it may read that fixed snapshot and invoke only a no-argument saturating fence-rejection capability. Fence accounting is bounded best effort after the authoritative stale-fence decision, so a connection, timeout or counter failure can omit the observation but never replace or materially delay the exact `409 stale_fence` result.

Every final application response with status 401 or 403 increments exactly once in a lock-protected process-local total, including missing/invalid credentials and scope, actor-kind, repository or trusted-authority rejection. That total has no labels or reset endpoint, starts at zero on socket-process restart, and never contains credential, actor or repository material.

M2/M3 producer handoffs keep their producer exact-base/head pairs. M4 validates closed shapes and cross-digest/SHA compatibility; it never invents those values from the current implementation commit. A fresh M0 observation (<=300 seconds) or named issuer/scope/expiry-bounded bootstrap exception is required at intake.

## Failure, rollout and recovery

Only database unavailable, worker lost, provider transport unavailable and temporary resource exhaustion are retryable. The frozen accepted `infrastructure_retries` limit persists per task and allows exactly zero, one or two retries after the initial attempt; the next typed infrastructure failure ends `dead`, while non-infrastructure failures require human review. Missing accounting blocks work; legacy unsafe claimable or positive endpoints are quarantined before readiness. A lone unsafe positive generation becomes explicit human recovery, while an unsafe older positive generation with a newer generation becomes `superseded/accounting_blocked` so the one-active-identity invariant and all accounting evidence are preserved. Ordinary event exhaustion cannot roll back mandatory lease/capacity cleanup or its audit fact. Kill switches block new claims while existing leases end cooperatively or expire. Source rollout is local/disposable only. Recovery is global kill, stop local intake/claims, preserve state/audit, restore a backup into a separate database for comparison, and forward-fix with migration `014+`.
