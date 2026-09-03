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

## Bounded architecture change policy

The original M2 `FIT-BOUNDED-ARCHITECTURE-CHANGE` remains exactly the six-prefix, `1,000,000`-byte / `10,820`-line / `5,000`-AST error rule accepted on base `67714a1...`; `factory` is not folded into or used to reinterpret it. Five additional error rules independently bound the seven-prefix aggregate (`1,300,000` / `24,000` / `5,000`), all of `factory` (`950,000` / `22,000` / `1,000`), `factory/src` (`235,000` / `5,500` / `650`), `factory/contracts` (`285,000` / `8,500` / `1`) and `factory/tests` (`340,000` / `7,500` / `350`). A matching artifact must satisfy every enclosing rule; complete path-segment matching excludes siblings, and unknown line metrics fail closed.

The amendment governs the exact-base aggregate instead of allowing minification or per-route partitioning to erase cumulative risk. Its implementation is representation-neutral: the complete factory, source, contract, test and migration trees remain byte-identical to the approved `5c5f111` freeze. The policy has no runtime, database, API, migration, external-operation or Trust CI effect.

## Integrity and concurrency

Intake separates three immutable identities. `intent_digest` binds the complete normalized intake, including transport `request_id` and the entire M0 proof, and remains the opaque persisted/M5 packet digest. `adaptive-factory.work-identity/v1` excludes only those two transport/observation fields and controls logical-work deduplication, while `adaptive-factory.intake-command/v1` binds one request ID to one full request/result in `command_results`. A refreshed valid M0 proof with a new request ID therefore returns the existing task; reuse of one request ID with a changed body conflicts; a changed semantic work field supersedes the active generation atomically.

Intake locks a stable source identity around semantic duplicate/supersession decisions. Claim uses database time, `FOR UPDATE SKIP LOCKED`, stable global/repository capacity locks, a strictly increasing task fence and one transaction for run/attempt/allocation/event/audit. Every worker mutation binds task, run, owner, role, fence, packet digest, current pointers, live task phase, live run/allocation, deadline, budget and command idempotency. One lock-neutral store primitive applies every task-state update through the operation-scoped policy after its caller has acquired locks in the established order; a denial rolls the containing transaction back. Fenced worker phase commands advance exactly through analyzing, implementing, verifying and reviewing without changing run state or the seven-field lease grant.

PostgreSQL 17 `factory.*` is the only M4 operational authority. Its migrations, registry, roles, credentials and search path are independent of Trust CI. Migrations are contiguous/checksum-locked under an advisory lock and forward-only after durable intake. Audit is insert-only and hash chained. Reconciliation performs ordered keyset work over at most 100 mutually exclusive candidates. One monotonic five-second deadline bounds the whole page through PostgreSQL 17 `transaction_timeout` plus decreasing statement timeouts; a statement timeout isolates a raced candidate after savepoint rollback, while a transaction timeout fails the operation and rolls back its partial batch.

## API, security and compatibility

The versioned API runs over an operator-owned Unix socket. Bearer tokens come from no-follow regular `0600` files, compare constant-time, map to closed scopes and are never logged. Socket mode is `0660`; bodies are at most 1 MiB; pages and projections are bounded. Runtime schema generation is disabled: the checked `factory-control.v1.json` is the sole reviewed HTTP contract, with exactly 17 stable operation IDs, closed inline request/response/error schemas, explicit parameters/statuses and response correlation headers. The CLI only calls the API. TCP, provider/Git/GitHub/deploy/systemd/external-write operations are absent.

Every application response carries a bounded `X-Correlation-ID`; mutation requests must supply it, while safe read responses receive a generated UUID when omitted. Errors share a bounded additive `error`/`code`/`detail` envelope, preserve the bearer challenge on 401 and redact internal exception text. Intake threads the transport correlation separately into command and audit evidence; neither correlation nor request replay identity changes semantic work deduplication. Event history exposes only the closed reviewed metadata superset, and malformed or unknown stored metadata fails the bounded read closed.

The authenticated metrics surface has three fixed families and no caller-controlled labels. Queue/state, transitions, leases, capacity, budget, kills and reconciliation/repair come from one fixed-row PostgreSQL snapshot maintained transactionally with authoritative writes and read under fixed 5-second statement and 500-millisecond lock timeouts. Runtime has neither table DML nor generic-key capabilities: it may read that fixed snapshot and invoke only a no-argument saturating fence-rejection capability. Fence accounting is bounded best effort after the authoritative stale-fence decision, so a connection, timeout or counter failure can omit the observation but never replace or materially delay the exact `409 stale_fence` result.

Every final application response with status 401 or 403 increments exactly once in a lock-protected process-local total, including missing/invalid credentials and scope, actor-kind, repository or trusted-authority rejection. That total has no labels or reset endpoint, starts at zero on socket-process restart, and never contains credential, actor or repository material.

M2/M3 producer handoffs keep their producer exact-base/head pairs. M4 validates closed shapes and cross-digest/SHA compatibility; it never invents those values from the current implementation commit. A fresh M0 observation (<=300 seconds) or named issuer/scope/expiry-bounded bootstrap exception is required at intake.

## Failure, rollout and recovery

Only database unavailable, worker lost, provider transport unavailable and temporary resource exhaustion are retryable. The frozen accepted `infrastructure_retries` limit persists per task and allows exactly zero, one or two retries after the initial attempt; the next typed infrastructure failure ends `dead`, while non-infrastructure failures require human review. Missing accounting blocks work; cancel, supersession and deadline cleanup preserve any unresolved reservation evidence and mark it as an explicit accounting quarantine. A deadline-expired clean task becomes `dead`; unresolved accounting becomes `needs_human/accounting_blocked`, and late workers remain stale-fenced. Ordinary event exhaustion cannot roll back mandatory lease/capacity cleanup or its audit fact. Kill switches block new claims while existing leases end cooperatively or expire.

This unaccepted repair candidate is schema-neutral and supports fresh PostgreSQL 17 bootstrap through exact schema `013` only. No M4 candidate has been accepted or authorized for persistent rollout, so there is no supported deployed schema-`013` upgrade population and no repair migration is required. An older unaccepted M4 database must remain killed and be preserved or restored only into a separate comparison database; it is not upgraded in place. Readiness detects unresolved terminal accounting without a quarantine marker and fails closed. Keeping the next numbers unused also avoids collision with provisional M5 migrations `014` through `017`; any future persistent repair needs a separately reviewed, dependency-coordinated forward migration.
