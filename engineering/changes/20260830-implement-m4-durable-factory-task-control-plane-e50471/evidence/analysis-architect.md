# Architecture analysis — M4 Durable Factory Task Control Plane

**Route:** `e50471553166`  
**Assessment mode:** read-only analysis of the approved roadmap against the current tree  
**Authoritative design source:** `DARK_FACTORY_ROADMAP.md`, sections 5–7 and M4 (lines 125–206, 529–603). The active change package is not yet an approved machine-readable specification: its Markdown plans are placeholders and `change-spec.yaml` contains template values.

## Executive assessment

M4 should be implemented as a new, independently deployable `factory/` service with its own PostgreSQL schema/database and least-privilege roles. It is a control plane only: it durably accepts, classifies, schedules, limits, and recovers factory tasks. It must **not** become an execution workspace (M5), semantic adjudicator (M6), PR automation (M7), or an alternative Trust CI authority.

The current tree contains no `factory/` service or factory state. Existing `trust-ci/` is a useful implementation reference for durable leases, retry, audit, API/worker separation, and PostgreSQL integration tests, but is a distinct trust domain and must not be reused as the factory queue. Therefore this is a greenfield vertical slice with prerequisite and design gaps that must be resolved before implementation passes the scope-and-design gate.

## Approved component boundaries

```text
authenticated GitHub Issue / authenticated operator CLI and API
  -> Factory intake API (validation, idempotency, supersession, audit)
  -> factory.* PostgreSQL (authoritative task/run/attempt/budget state)
  -> Scheduler/reconciler (admission control, leases, expiry recovery)
  -> M5 execution-plane adapter (future; no workspace execution in M4)

Factory control plane -- immutable task/result references only --> Trust CI and later PR lifecycle
Trust CI -- App-owned exact-SHA merge verdict --> GitHub branch protection
```

Required boundaries:

- `factory/` owns task lifecycle, active-task admission, lease ownership, budget accounting, task audit, and reconciliation. PostgreSQL `factory.*` (or a separate factory database) is authoritative for that state.
- The intake API authenticates callers and validates typed references; it does not have a Trust CI signing key, GitHub App key for authoritative checks, human approval private key, or production credential.
- Scheduler/worker identity is distinct from API identity. It may claim/heartbeat/transition only a currently fenced attempt; it cannot bypass admission, approval, or audit rules.
- M4 dispatches only a bounded task packet reference. M5 later owns branches, isolated workspaces, short-lived task secrets, egress, and implementation execution.
- Trust CI keeps ownership of `trust_ci.*` jobs, approvals, attestations, external holdout evaluation, and the GitHub App-owned policy-epoch check. Factory state may link to a check/attestation by immutable identifiers but cannot publish or mark its result authoritative.
- M1 supplies the accepted typed change-spec digest; M2 supplies architecture-model/policy digest and fitness constraints; M3 supplies reviewed governance/debt references. M4 must consume these immutable versions rather than reconstructing them from Markdown.

## Durable model and contracts

### Immutable contracts

Define versioned, frozen contracts before code:

- `TaskRequest` (external input): repository, source type/id, exact base SHA, accepted `change_id`, `route_id`, spec/architecture/policy digests, requested priority, and caller idempotency key. It must reject free-form execution commands, secrets, mutable branch names as authority, and unpinned artifact references.
- `FactoryTask` (immutable identity/version): includes the roadmap minimum fields: `task_id`, repository, source metadata, route/change identifiers, spec and architecture digests, base/head SHA when known, branch when known, pre/post risk, policy digest, attempt/lease fields, budget, timestamps. Add `contract_version`, idempotency key, active-generation/supersession linkage, and immutable intake payload digest.
- `TaskRun` and `TaskAttempt`: immutable run/attempt records with actor/role, task packet digest, start/end timestamps, outcome/failure class, resource measurements, lease/fencing token, and artifact references. A later retry creates a new attempt; it does not rewrite a completed attempt.
- `StateTransition` / audit event: append-only record with transition id, task id, expected predecessor state, successor state, actor type/id, reason code, correlation id, timestamp, and payload digest. Mutable task projection is derived from successfully committed transitions.
- `BudgetPolicy` and `CapacityPolicy`: versioned policy snapshots referenced by digest, carrying global/per-repository active task and PR caps, writer/read-only limits, runtime/token/cost/repair/PR-age ceilings, and admission behavior. A task snapshots the applicable policy; a stricter emergency control can still stop it.

Idempotency must be a database-enforced uniqueness rule over the normalized source identity plus exact base SHA plus accepted spec digest plus architecture/policy version (the roadmap wording is source, base SHA, policy/spec version). It applies only to active/nonterminal generations. A duplicate returns the existing task identifier and does not consume capacity.

### API/CLI surface

Expose a small authenticated local API and matching CLI, with JSON schemas/OpenAPI checked in under `factory/`:

- `POST /v1/tasks`: authenticated intake; accepts an idempotency key; returns `201` for new task and `200` for exact duplicate. `409` identifies a stale/superseded source version; `422` invalid contract; `429`/`503` admission or kill-switch refusal without deleting evidence.
- `GET /v1/tasks/{task_id}` and filtered list endpoints: read-only task projection, current state, immutable references, budget summary, and safe audit view. Authorization is repository-scoped.
- `POST /v1/tasks/{task_id}/cancel` and named human-control endpoints for global/per-repository stops: privileged, audited, idempotent; never erase task/run/audit evidence.
- Internal worker endpoints or direct database repository methods for claim, heartbeat, fenced transition, and reconciliation only. They are not public intake APIs.
- CLI mirrors these actions, uses the same authentication and correlation/idempotency semantics, never writes directly around the API, and never carries long-lived secrets in task data/logs.

GitHub Issue intake is a producer, not an authority. Verify webhook authenticity, canonicalize repository/source identity, fetch/reconcile issue revision safely, and preserve the delivery id for deduplication. Manual intake requires authenticated local callers and explicit repository authorization.

## State machines and concurrency rules

The required task projection is:

```text
inbox -> triaged -> waiting_approval -> queued -> leased
      -> analyzing -> implementing -> verifying -> reviewing
      -> pr_open -> ready -> merged

exceptional: retry, needs_human, dead, cancelled, superseded
```

M4 should implement the durable portion through `queued`, `leased`, and recovery/terminal exceptions. Later-phase states may be represented as declared transitions but must not pretend M4 executes M5–M7. Valid transition guards should include:

- Intake creates `inbox`; successful contract/risk classification moves it to `triaged`. Missing named approval moves it to `waiting_approval`; only a validated approval/release of that condition can queue it.
- Admission atomically checks kill switches, exact duplicate, repository/global WIP, per-repository writer/read-only capacity, and all relevant budgets before `queued`. Refusal is audit-visible and non-destructive.
- Claim uses one transaction with `SELECT … FOR UPDATE SKIP LOCKED`, a live-capacity check, a new monotonically increasing `attempt_no`, and a fresh opaque fencing token. It changes only an eligible queued/reclaimable task to `leased`.
- Heartbeat, phase transition, completion, and budget debit require `(task_id, attempt_no, fencing_token, lease_owner, lease_expires_at > database_now())`. This prevents a reclaimed/partitioned worker from committing after its lease has been superseded.
- Lease expiry leaves evidence intact. Reconciliation records the loss, releases live capacity exactly once, and either requeues with backoff (while limits remain) or marks `dead` after the bounded attempt ceiling. No active task may loop indefinitely.
- Source changes (Issue revision), base SHA changes, accepted-spec changes, or policy/architecture digest changes atomically supersede all older nonterminal generations before a new generation is admitted. A stale worker cannot revive a superseded task because its fencing token no longer matches.
- Cancellation/kill switch prevents *new dispatch* and claims. It must define whether a running leased task is allowed to finish, asked to stop cooperatively, or expired/reclaimed; the policy must select one explicit behavior. M4 must not silently delete or force-terminalize a task without an audit record.

## Data integrity, failure, and recovery design

Use PostgreSQL transactions and constraints as the concurrency authority, not process memory. Minimum tables: `factory_tasks`, `factory_task_generations` (if task identity is separated from source generation), `factory_runs`, `factory_attempts`, `factory_state_transitions`, `factory_capacity_reservations`, `factory_budget_ledger`, `factory_kill_switches`, and `factory_reconciliation_runs`. Foreign keys must preserve audit evidence; avoid cascading deletes from tasks to attempts/audit.

High-risk failure modes and required controls:

| Failure mode | Required behavior |
| --- | --- |
| Duplicate webhook/API retry | Unique idempotency index returns original active task; audit duplicate receipt. |
| Two schedulers/workers race | `SKIP LOCKED` claim plus row/version check and attempt fencing; one live owner only. |
| Worker dies/network partitions | Lease expires by database time; reconciler releases reservation, creates bounded retry/dead-letter outcome. |
| Old worker resumes | Fencing token rejects heartbeat, state changes, budget writes, and result publication. |
| PostgreSQL restart | Committed state/audit persists; reconciling claim path recovers expired leases; no in-memory queue is authoritative. |
| Budget/capacity race or crash | Reserve/debit/release transactionally with attempt state; reconciliation repairs only from durable ledger evidence. |
| Source/spec/base/policy drift | Supersede nonterminal generation atomically; do not dispatch stale immutable packets. |
| Trust CI unavailable | Refuse dispatch unless an explicitly named, recorded bootstrap exception exists; do not treat local checks as equivalent. |
| Kill switch activation | Stop admission/claim, retain evidence and expose stop reason/actor; recovery requires a separate audited release. |
| Unauthorized operator or cross-repository access | Server-side repository-scoped authorization on every resource; audit denied attempts without secret material. |

Dead-letter is an evidentiary terminal state, not an automatic repair trigger. Requeue requires a distinct authorized, audited generation/action with a reason and fresh capacity/budget admission.

## Trust boundaries and security assessment

Assets: task packets and source references, repository authorization, task and audit integrity, budget/capacity limits, PostgreSQL credentials, local API credentials, and links to exact-SHA Trust CI evidence. Actors: GitHub webhook sender, authenticated operator, scheduler, worker, reconciler, Trust CI service, and future executor.

The dominant abuse cases are forged/replayed intake, tenant/repository confusion, duplicate work to bypass WIP/cost caps, stale-worker writes, cancellation bypass, budget ledger tampering, and factory-to-Trust-CI privilege escalation. Controls must include authenticated/verified intake, authenticated internal roles, repository-level server-side authorization, least-privilege database roles, SQL parameterization, bounded request sizes/rate limits, opaque secrets redaction, append-only audit, correlation IDs, fenced leases, and independently reviewed schema/contract migrations.

Do not mount or request Trust CI signing keys, GitHub App credentials that publish the authoritative check, human approval keys, production credentials, or execution-plane secrets in the factory API/worker. This preserves the roadmap's required separation even if both services use PostgreSQL.

## Observability and operational signals

Every task/run/attempt/audit record carries a correlation id. Export metrics at least for intake outcomes/duplicates/rejections, state transition counts, queue age, ready/leased counts, lease-expiry/reclaim count, fencing rejections, retry/dead-letter count, kill-switch state, source supersession, repository/global WIP, active writers/readers, reservation and budget consumption/exhaustion, reconciliation duration/repairs, and API authorization failures. Tag by repository only if cardinality and privacy policy permit; use bounded task/risk/state labels rather than task IDs.

Alerts: stuck queue/oldest queue age, expired leases not reconciled, reconciliation failure, capacity leak, budget ledger imbalance, dead-letter surge, kill switch active unexpectedly, unavailable Trust CI admission gate, and repeated authorization failures. Logs and audit views must store digests/references, not credentials, prompt bodies, or unbounded agent output.

## Rollout and rollback

Roll out in a non-dispatching shadow mode first: accept/validate/deduplicate/audit tasks and exercise scheduler/reconciler against an isolated test repository or dry-run adapter; enforce kill switches, WIP, and budgets before any execution-plane or GitHub write capability is connected. Use real PostgreSQL integration tests for concurrent claim, lease expiry/reclaim, fencing rejection, attempt exhaustion, restart recovery, stale supersession, capacity/budget races, and authorization.

Migration rollout is expand/contract: add `factory` schema/database and roles without touching `trust_ci` tables; deploy readers compatible with both migration versions; backfill only bounded derived projections with checkpoints; then enable admission. No destructive migration without the named approval. Rollback is primarily kill switch + disable intake/dispatch. Preserve all rows/audit, stop new work, and forward-fix projections/schema incompatibilities; database restore is reserved for proven corruption and requires the designated approval/recovery evidence.

## Current-tree comparison and blockers

1. **M4 service absent (blocking implementation scope gap).** `git ls-tree -d --name-only HEAD` has no `factory/`; current top-level files have only `trust-ci/` as a scoped service. Create the recommended isolated service boundary; do not add a root packaging marker.
2. **M4's prerequisite interfaces are not all available (blocking design gap).** M1 has `schemas/change-spec.schema.json`, `.grok-stack/adaptive_grok/spec.py`, and `scripts/grok_spec.py`. M2's prescribed `architecture/system.yaml`, `architecture/rules.yaml`, schema, validator, and fitness functions are absent. M3's governance/debt schemas and lifecycle implementation are absent. M4 cannot safely invent mutable substitutes for their digests; either implement/approve stable prerequisite interfaces first or record an explicit, bounded bootstrap exception with immutable surrogate artifacts.
3. **The active change package is not an approved executable design (blocking scope-and-design gate).** `brief.md`, `requirements.md`, `architecture.md`, test/release/rollback plans are blank templates; `change-spec.yaml` has `{{OBJECTIVE_STATEMENT}}`, `UNKNOWN`, placeholder risk/rollback, and no acceptance criteria, invariants, contracts, observability, or approval scopes. It does not meet the M1 schema/roadmap exit criteria and cannot drive intake or evidence.
4. **Do not reuse Trust CI tables or generalize `trust_ci_jobs` (hard boundary).** `trust-ci/sql/001_schema.sql` implements PR verification job state only; its statuses and identifiers lack source/change/spec/architecture/budget/fencing semantics. Roadmap section 6.2 explicitly forbids turning it into the factory queue. Its reusable patterns are conceptual only.
5. **Existing Trust CI schema naming strengthens the need for a separate factory database/schema.** Although the roadmap calls for `trust_ci.*`, current Trust CI migrations use the PostgreSQL `public` schema and roles grants directly on `trust_ci_*` tables. Factory migrations must neither alter those tables nor depend on its `public` schema defaults. A distinct factory database is the clearest isolation; otherwise explicit `factory` schema, role search paths, grants, backup/restore ownership, and migration isolation are mandatory.
6. **Trust authority is not live by repository declaration (dispatch blocker absent an exception).** `README.md` states the App-owned check is not live and calls PR #2 a bootstrap exception. M4 must fail dispatch when M0 is unavailable unless the user records the roadmap-required named bootstrap exception. Local verification and receipts remain preflight only.
7. **No factory-specific contracts, migrations, API auth model, capacity policy, reconciliation policy, or PostgreSQL test environment exists.** These must be explicit before code, not inferred from the Trust CI implementation. In particular, leases without a fencing token are insufficient for the M4 stale-worker failure mode.
8. **No external writes or production mutation are authorized by this task.** M4 implementation can provide local/test-only interfaces and real disposable PostgreSQL tests, but GitHub Issue webhooks, operational deployment, production database migration, branch/PR creation, check publication, or changes to Trust CI deployed policy/holdout are out of scope unless separately delegated and approved.

## Scope ruling

Proceed only after the scope-and-design approval resolves items 2–3 and records: the selected factory database/schema and roles, the exact M1/M2/M3 artifact versions (or approved bootstrap exception), versioned API/event schemas, state-transition/fencing matrix, capacity and budget policy, kill-switch semantics, and migration/rollback plan. The first implementation slice should stop at durable authenticated intake, audited idempotency/supersession, PostgreSQL fenced leases, bounded recovery/dead-letter, capacity/kill-switch admission, reconciliation, and integration tests. It should expose no execution, PR, merge, Trust CI publication, or production-write capability.
