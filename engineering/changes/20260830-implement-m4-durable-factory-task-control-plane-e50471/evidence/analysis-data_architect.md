# Data architecture analysis — M4 Durable Factory Task Control Plane

**Route:** `e50471553166`  
**Reviewed:** 2026-08-31  
**Sources:** approved M4 plan at `feature/model-agnostic-factory:docs/superpowers/plans/2026-08-28-m4-durable-factory-control-plane.md`, its design specification and roadmap, reviewed M3 ref `milestone/m3-controlled-knowledge-debt` (`d4cc01fe`), and routed base `1c062998`.

## Verdict

**BLOCKED at scope/design gate.** The plan correctly requires M4 to be stacked on the exact reviewed M3 head and to consume frozen M1/M2/M3 handoffs. The route instead pins `1c062998`; it is neither an ancestor of reviewed M3 `d4cc01fe` nor does it contain M2/M3's required interfaces. In particular, the route base lacks `.grok-stack/adaptive_grok/{architecture,governance}.py`, `architecture/{system,rules}.yaml`, and `schemas/governance-handoff-v1.schema.json`. M3's own evidence says its final handoff must be re-derived on the final head and that M4 is a separate stacked PR after M3. No factory task can truthfully validate the required frozen inputs from this base.

Before implementation, record one of these bounded decisions: rebase/stack M4 on the exact reviewed M3 head (and rederive the handoffs on the eventual M4 head), or approve a versioned compatibility handoff implementation with its own schema and migration/rollback contract. Do not manufacture mutable Markdown substitutes.

## Required durable boundary

- Create a separate `factory` database where possible. If one PostgreSQL cluster must be shared, create an explicit `factory` schema, factory-only migrator/runtime/read-only roles, `search_path=factory,pg_catalog`, schema-qualified SQL, explicit ownership/default privileges, and separate backup/restore ownership. The factory runtime must have **no** grants on `public` or `trust_ci.*`.
- Do not adapt `trust_ci_jobs` or `trust_ci_schema_migrations`. Current Trust CI uses unqualified tables in `public`, roles `trust_ci_*`, and a PR-verification state machine. It cannot express immutable handoffs, task/run fences, 20/10/1 capacity, budgets, or M4 reconciliation; sharing it also violates the plan's hard authority boundary.
- Factory migrations need their own stable advisory-lock namespace and immutable registry `factory.schema_migrations(version, name, sha256, applied_at)`. Apply pending migrations and registry records in one transaction; reject gaps, renamed files, and checksum drift. Migrations must be expand/contract only; no destructive rollback. Operational rollback is disable intake/claims with a global kill switch, preserve rows/audit, then forward-fix.

## Schema and integrity requirements

The plan's three migrations form a sound minimum: immutable `accepted_intents`; task current projection plus append-only task/audit events; runs/attempts/lease generations/capacity allocations; budgets/usage/kills/reconciliation. Enforce, rather than merely validate in Python:

- unique accepted-intent digest and intake idempotency key; an identity row keyed by `(repository_id, source_type, source_id)` provides a fixed row to serialize competing intake/supersession transactions;
- task events unique on `(task_id, event_sequence)` and proposal commands unique on their idempotency key; replay may return an original outcome only when the stored payload digest matches;
- foreign keys include task identity where needed to make cross-task run/event/allocation references impossible; `attempt_no >= 1`, counters/cost/tokens non-negative, deadline `<= accepted_at + interval '4 hours'`;
- a monotonic fence per task (or task generation) advanced only in the claim transaction. A run grant must bind task/run/owner/fence/packet digest/expiry; all mutations must predicate on every one of those values;
- a unique active allocation for a run and a partial unique index for the unreleased global writer allocation. Counter rows remain useful for 20 global readers and 10 readers/repository, but are only correct if locked and updated in the same transaction as the allocation.

`audit_log` should be append-only to the runtime role: grant only `INSERT, SELECT`, revoke `UPDATE, DELETE, TRUNCATE`, and test these permissions with that role. A hash chain detects accidental/tampering evidence after access but is not a replacement for database backups and role separation.

## Transaction, lock, and query-plan rules

1. **Intake/supersession:** lock the `(repository, source)` identity row first; insert immutable intent with `ON CONFLICT`/lookup; return the existing exact idempotency task or supersede eligible nonterminal tasks and create the replacement. Write task event and audit row in this same transaction. Never overwrite intent JSON.
2. **Claim:** set a local 5-second statement/lock timeout; lock global and repository counter rows in a total deterministic order, check kill switches, select one eligible task using an index-backed `FOR UPDATE SKIP LOCKED`, then allocate capacity, increment fence, create run/attempt, set lease expiry bounded to task deadline, and append event/audit before commit. All contenders must take locks in the same order to avoid deadlocks.
3. **Heartbeat/proposal/release:** one guarded `UPDATE ... WHERE task_id/run_id/owner/fence/packet_digest match AND lease_expires_at > now() AND status is expected`; inspect affected row count and distinguish stale fence from invalid state. Usage, state proposal, terminal transition, allocation release, and counter decrement must be in one transaction.
4. **Budget:** lock the task budget aggregate before reservation. Compare reserved plus trustworthy observed usage against integer-micro USD/token/wall limits. Deduplicate observations on `(run_id, provider_call_id)`, retain price-table digest/provenance, and mark accounting blocked on absent/invalid metering; do not assume zero.
5. **Reconciliation:** scan a stable ordered keyset in bounded batches of 100 under a 5-second timeout. Each reclaim/terminal-projection repair must have an idempotent event key and atomically release allocation/counters exactly once. It must handle expired leases, orphan allocations, expired deadlines, accounting blocks, stale frozen inputs, and incomplete terminal projections.

Indexes must be demonstrated with `EXPLAIN (ANALYZE, BUFFERS)` against representative queued/leased and multi-repository data: eligible claim predicate/order, lease-expiry reconciliation, task list `(created_at, task_id)` keyset pagination, source identity lookup, live allocations by role/repository, budget aggregate, and reconciliation cursor. Partial indexes should include only live/unreleased or active statuses. Avoid wide JSONB index scans; immutable bodies are evidence, not query surfaces.

## Capacity, lease, retry, and recovery correctness

- Capacity authority is PostgreSQL, not worker count: readers <=20 globally and <=10 per repository, writers <=1 globally. Counters have `CHECK >= 0`, allocations have database uniqueness, and every reclaim/release decrements in the same transaction. Reconciliation must repair an allocation/counter mismatch idempotently.
- A lease is never a fence. Expiry/reclaim must produce a strictly higher fence; any old heartbeat/proposal/usage/release is rejected even if the worker still runs. Lease seconds are 30..300 and cannot pass the four-hour task deadline.
- Increment attempt count only on a successful grant. Only listed typed infrastructure failures retry; attempt 3 transitions atomically to `dead`, retains evidence, and releases capacity. All other failures terminate/escalate according to closed state policy.
- Kill switches block only new claims. They retain live evidence and leases; policy must state whether live work finishes cooperatively or is reclaimed after expiry, and the implementation must audit the choice. Cancellation likewise cannot delete durable evidence.

## Migration, recovery, and test-database strategy

Use an operator-provided, disposable `FACTORY_TEST_DATABASE_URL` or the isolated `factory/compose.yaml` PostgreSQL 15+ service. Tests must never inspect `.env` or reuse Trust CI URLs/schemas/roles. Apply M4 migrations to a fresh test database; record only PostgreSQL version, migration checksums, test names/counts, duration, and result. Stop the compose project only if the test started it; retain/remove its named volume only through the documented disposable cleanup path.

The real-PostgreSQL exit group must concurrently prove exactly-one duplicate intake, competing claim serialization, 20/10/1 limits, fenced late result rejection after worker loss/reclaim, initial plus two retry exhaustion, trusted-usage budget blocking, kill-switch claim blocking without evidence loss, and restart-safe reconciliation. Add a two-process late-result drill; fake-store tests cannot establish transaction or lock correctness.

## Blocking evidence from reviewed M3 and base divergence

`milestone/m3-controlled-knowledge-debt` has approved package state but its release plan says M4 follows M3 as a separate stacked PR and requires a current exact M1/M2/M3 handoff. Its task ledger explicitly says final M3 handoffs must be rederived on the final fingerprint. The active route's base `1c062998` is divergent, while M3 is `d4cc01fe`; `git merge-base --is-ancestor` is false in both directions. This prevents valid M4 intake validation and the plan's Task 9 M2 boundary update on the chosen base.

No production migration, external write, Trust CI mutation, or Trust CI credential/approval/key access is authorized or necessary for this analysis.
