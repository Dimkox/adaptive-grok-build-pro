# Architecture analysis — bounded M4 local control-plane feature

**Route:** `b7f288f1e81e`
**Required implementation base:** `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
**Observed branch head:** `67714a1…`, which contains accepted M2 `022411b…` and accepted M3 `1e73ff9…`.
**Scope:** source-level local feature only; no execution provider, network side effect, deployment, GitHub write, Trust CI authority, or production mutation.

## Pre-write gate: rebind the route and handoffs

The active route/package still declare `base_commit: 1c062998…` even though the task and current HEAD require `67714a1…`. That mismatch is a hard stop for implementation: regenerate the route/change binding and create the M4 package on the exact accepted base before the write owner changes application code. Do not alter M4 inputs to make the old route appear compatible.

At submit time, each accepted task must freeze references to:

- the validated M1 change-spec canonical digest/fingerprint and its stable criterion/invariant/forbidden-outcome IDs;
- independently derived M2 architecture evidence/digest, including exact M2 comparison base/head and required scopes;
- closed M3 `GovernanceHandoffV1` fields (`governance_contract_version`, governance/evidence digests, architecture digest, exact base/head) rederived from the accepted baseline;
- exact factory policy/limit digest, route id, change id, source revision, and base SHA.

Any absent, malformed, stale, cross-boundary, or nonmatching input fails closed. Repository Markdown, local receipt text, caller-provided approval-looking metadata, and route state are references only; they cannot substitute for a validated frozen handoff.

## Bounded service shape

Create one scoped `factory/` Python application feature, not a new deployed service:

```text
factory/
  contracts.py           closed dataclasses/JSON contract validation and canonical digests
  state.py               exhaustive transition/retry rules; no I/O
  migrations.py + sql/   factory-only immutable migration history/checksums
  store.py               PostgreSQL transactions, locks, fencing, role-safe queries
  service.py             typed use cases and authorization decisions
  api.py                 Unix-domain-socket JSON request adapter only
  cli.py                 local operator client; never bypasses API/service policy
  observability.py       bounded counters and redacted audit projection
  tests/                 unit, contract, and disposable PostgreSQL integration tests
```

The API and CLI run locally over an operator-owned Unix socket; do not add HTTP listener, webhook receiver, queue, container topology, systemd unit, external SDK, background execution provider, or GitHub client. PostgreSQL is durable local state, not a Trust-CI dependency: prefer a distinct factory database; if a disposable shared cluster is necessary, use a dedicated `factory` schema, roles, search paths, migration ledger, backup/restore ownership, and no grants to `trust_ci_*` objects. This is a new datastore/architecture surface and therefore remains behind the route's scope-and-design and migration gates; it is not a new remotely deployed service.

## Contracts and module boundaries

`contracts.py` owns closed versioned `TaskIntakeV1`, `FactoryTaskV1`, `FactoryRunV1`, `FactoryAttemptV1`, `CapacityPolicyV1`, and `FactoryEventV1` records. The immutable task packet includes source/repository identity, route/change ids, all M1/M2/M3/policy digests, exact source/base SHA, risk, acceptance IDs, idempotency key, budget ceilings, and correlation id. Reject unknown fields and unpinned digests.

`state.py` owns pure validation. Task projection states are restricted to:

```text
inbox -> triaged -> waiting_approval -> queued -> leased -> ready_for_human
                         \                         \
                          needs_human                retry -> queued | dead

terminal: dead, cancelled, superseded
```

`ready_for_human` is the only normal positive M4 terminal state. `analyzing`, `implementing`, `verifying`, `reviewing`, PR, merge, and deployment states belong to M5–M9 and are invalid M4 transitions. Supersession/cancellation retain immutable intent, run, attempt, event, and audit records.

Each lease creates an immutable `run` and `attempt` with a monotonically increasing fence. The mutable task projection holds the current attempt/fence only as a denormalized index. Every worker-facing mutation requires task id, run id, attempt, current owner, fence, packet digest, idempotency key, permitted predecessor state, unexpired database-time lease, deadline, and budget allocation. A stale/expired/reclaimed attempt cannot heartbeat, propose, debit, release, or complete.

`store.py` is the only module with SQL. It applies migrations under an advisory lock, uses `SELECT … FOR UPDATE SKIP LOCKED` for claims, locks global then repository capacity in a fixed order, inserts the fence/allocation/event/audit in the same transaction, and uses append-only audit/event tables with no cascade deletion. Retry is only for typed infrastructure failures; initial attempt plus two retries is the hard ceiling, then `dead`. Reconciliation has an ordered 100-candidate/5-second-statement bound, is idempotent, and repairs expired leases, capacity allocations, budget reservations, stale inputs, and accounting only through durable evidence.

## Local API and CLI contract

Expose versioned, schema-validated Unix-socket operations only:

```text
health
submit        show/list        cancel
claim         heartbeat        proposal/release
kill on/off   reconcile
```

`submit/show/list/cancel` are repository-scoped operator/client actions; claim/heartbeat/proposal/release and kill/reconcile have separate internal/operator scopes. The socket API authenticates a local bearer token from a no-follow, mode-0600 operator-owned file using constant-time comparison. Socket permissions are `0660` under an explicitly owned runtime directory. All requests have byte, field, page, deadline, idempotency, and correlation limits. Responses/audit projections are redacted and bounded; neither API nor CLI accepts shell commands, provider configuration, prompt content, secrets, Git credentials, deployment controls, Trust CI checks, or production actions.

The CLI is an unprivileged transport client—no direct database connection and no second authorization path. It serializes the same contract, receives safe structured errors (`invalid`, `unauthorized`, `conflict/stale fence`, `capacity/budget stop`, `killed`, `not found`), and never logs a token or raw request body.

## Data flow and safety controls

```text
validated M1/M2/M3 frozen handoffs + local caller
  -> Unix-socket API auth/bounds
  -> service admission (kill, authorization, idempotency, limits)
  -> factory PostgreSQL transaction
  -> immutable task/run/attempt/event/audit + mutable projection
  -> bounded scheduler/reconciler commands
  -> ready_for_human or evidence-preserving exception state
```

Idempotency is a database uniqueness rule over normalized source identity plus exact base SHA and frozen M1/M2/M3/policy digests for nonterminal work. The exact duplicate returns the existing task. Changed source revision, base SHA, spec/architecture/governance/policy digest atomically supersedes older nonterminal work before admitting the new generation. Capacity is limited to 20 global readers, 10 readers per repository, and one live application writer. Runtime (four hours), cost (USD 25), token/output/event/repair ceilings and missing price/usage evidence stop work fail-closed.

Global and repository kill switches block new intake admission/claims while preserving evidence. They do not delete rows, force a success, remove Trust CI protection, or stop later reconciliation. There is no outbox because M4 emits no external event or side effect; `FactoryEventV1` and audit are local durable facts only.

## Observability, rollout, and rollback

Use low-cardinality counters/histograms for intake/duplicate/reject, transition, queue age, lease expiry/reclaim, stale-fence rejection, active capacity, reservation/usage/budget stop, retry/dead-letter, supersession, kill state, reconciliation repair/failure, and authorization failure. Correlation ids belong in bounded redacted logs/audit, not metric labels. Never record secrets, raw prompts/bodies, reasoning, tokens, GitHub credentials, high-cardinality task IDs, or process output in metrics.

First release is source plus disposable PostgreSQL integration evidence only. A later separately approved local activation starts with kill enabled, validates migration checksums and a backup, performs one synthetic submit/claim/heartbeat/release/restart/reconcile drill, then clears the switch. It does not deploy a new network service or perform external writes.

Rollback: enable global kill, stop intake/claims/local socket process, retain all state/audit/backup evidence, and forward-fix in a new migration/PR. Before any disposable intake, test cleanup may remove the named disposable factory schema. After durable intake, never down-migrate/delete audit; restore a verified backup into a separate database for comparison and add migration `004+` (or later) only with fresh review/approval. Trust CI state, policy, holdout, keys, GitHub checks, and branch protection are never touched.

## Required architecture and verification evidence

The implementation must update the M2 architecture model/rules and diagrams to declare the local factory application, factory state boundary, contracts, data classification, no-network Unix-socket control edge, secrets prohibition, failure signals, and explicit separation from all Trust-CI nodes. This adds a datastore and new local component, so post-diff risk remains red and requires the named architecture/data/security review; do not hide it as an undocumented library. The architecture model must state that the factory node has no edge to Trust CI, runner, holdout, GitHub, or production trust domains.

Before scope approval, complete the change spec with stable acceptance/invariant/forbidden-outcome IDs and map it to the implementation tests below. The minimum real PostgreSQL suite proves duplicate intake, two concurrent claims, global/repository capacity, late fence rejection after expiry/reclaim, bounded retry/dead-letter, stale supersession, budget/WIP/kill stops, role separation from Trust CI, restart recovery, and idempotent bounded reconciliation. Also test socket auth/scopes/body limits/redaction, migration checksum/role drift, contract unknown fields, and the explicit absence of execution/external-write operations. Final completion additionally requires architecture validation/diagram check, final `grok_verify --mode pr`, all five route reviews, fresh fingerprint-bound receipts, README parity, and the App-owned exact-head Trust CI check.
