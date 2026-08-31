# M4 task analysis — exact accepted-M3 base

Route: `b7f288f1e81e`
Change: `20260831-implement-a-new-m4-application-feature-on-exact-b7f288`
Actual worktree HEAD: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1` (merge of M3 PR #11)
Sources: `DARK_FACTORY_ROADMAP.md` M4; `docs/superpowers/specs/2026-08-26-model-agnostic-autonomous-factory-design.md`; `docs/superpowers/plans/2026-08-28-m4-durable-factory-control-plane.md`; prior M4 analysis in `/home/pall/grok-projects/adaptive-grok-build-pro/engineering/changes/20260830-implement-m4-durable-factory-task-control-plane-e50471/`.

## Scope ruling and immediate gate

M4 is now correctly positioned after M3: this worktree contains M2 architecture and M3 governance interfaces, and HEAD is the user-named exact accepted-M3 base. The prior route's missing-handoff blocker is resolved **for this worktree**.

However, `active-route.json` still declares `base_commit: 1c062998...` and fingerprint for that prior base while its task says exact base `67714a1...`. Before implementation, refresh/re-route or record a scope/design ruling that binds the route/change/evidence to `67714a1...`; otherwise the local receipts and external exact-SHA evidence cannot be accurately bound. The gate is required by the route (`scope_and_design_approval`) and is a short administrative correction, not a reason to recreate M2/M3.

The migration gate must approve only a disposable factory test/staging database and isolated roles/schema; M4 performs no production or external write.

## Observable outcome

An authenticated local operator submits a closed, immutable M1/M2/M3-bound intent and receives one durable factory task. PostgreSQL, not worker memory, makes duplicate intake, stale-worker proposals, capacity overflow, retry exhaustion, budget overrun, cancellation, and restart recovery deterministic. The result is a local control-plane source feature; it never executes a provider/repository command or creates a network side effect.

## Exact acceptance criteria

1. **Isolation and authority.** A nested `factory/` package owns a factory-only PostgreSQL schema/database, migrations, roles, API, CLI, and tests; root packaging markers remain absent. It must neither import/query/reuse `trust_ci.*`, Trust CI jobs/approvals/attestations, keys, holdout, policy, or App credentials.
2. **Frozen typed intake.** Closed, immutable contracts validate `TaskIntakeV1`, `TaskLimitsV1`, M2 `ArchitectureHandoffV1`, M3 `GovernanceHandoffV1`, actors, tasks/runs/attempts, and canonical SHA-256 JSON. Intake requires valid matching frozen M1 spec/M2/M3/policy digests, exact 40-hex base SHA, current M0 observation (<=300 seconds) or named bootstrap exception, bounded NFC fields, sorted unique acceptance IDs, and ceiling limits. Unknown fields/versions, invalid or mismatched digests/SHAs, stale M0, and missing/invalid accounting fail closed.
3. **Idempotent immutable intake.** The canonical idempotency key binds repository, source identity/digest, base SHA, spec, architecture, governance, and policy. Identical concurrent delivery returns one active task; changed source/base/spec/architecture/governance/policy creates a replacement and atomically supersedes eligible nonterminal work. Accepted intent JSON is never overwritten.
4. **Closed M4 state/failure policy.** Support only `inbox`, `triaged`, `waiting_design_approval`, `queued`, `leased`, `analyzing`, `implementing`, `verifying`, `reviewing`, `ready_for_human`, plus `retry`, `needs_human`, `dead`, `cancelled`, `superseded`. Reject future delivery states (`pr_open`, `merged`, deployment). Only authenticated control-plane commands may transition; `needs_human -> queued` requires a persisted operator decision; terminal states remain terminal. Provider/untrusted text cannot select state, retry class, budget, authority, or capability.
5. **Durable migrations and integrity.** Immutable contiguous checksum-verified `factory.schema_migrations` under a factory advisory lock create accepted intents, tasks, events/audit, runs/attempts/fence sequence/capacity allocations, budgets/usage/kills/reconciliation. Constraints enforce idempotency/event/proposal uniqueness, task-local foreign keys, non-negative counters, <=4-hour deadline, and live allocation/writer correctness. No destructive/down migration after durable intake.
6. **Lease, fence, and capacity correctness.** Claim uses PostgreSQL `FOR UPDATE SKIP LOCKED`; every heartbeat/proposal/release verifies task/run/owner/current state/packet digest/deadline/budget/idempotency and monotonic fence in one transaction. Two workers cannot own a live task; after expiry/reclaim the old worker cannot heartbeat or commit. Enforce at most 20 global readers, 10 readers per repository, and exactly at most one live application writer in database transactions.
7. **Bounded retry, budgets, and WIP.** Only the closed infrastructure failure set retries; initial + two retries only, with the third ending in `dead`. Enforce 4 hours, USD 25 aggregate reservation (25,000,000 micros), 2,000,000 tokens, bounded event/output bodies, WIP/open-PR limits, and reserved 1–3 semantic repair capacity (not executed by M4). Missing trusted metering/pricing blocks work rather than charging zero.
8. **Safety controls and audit.** Authenticated global/per-repository kill switches block new claims without deleting evidence. Append-only hash-chained audit events retain bounded actor/action/resource/reason/metadata and runtime database roles cannot update/delete them. Cancellation likewise preserves evidence.
9. **Bounded restart-safe reconciliation.** A 100-item keyset-bounded, 5-second-timeout, idempotent reconciliation repairs expired leases, orphan allocations, deadline/accounting blocks, stale frozen input, and incomplete terminal projections exactly once; it releases allocations/counters atomically and is safe to repeat after process restart.
10. **Local API/CLI contract.** Versioned `/v1` Unix-socket HTTP and CLI expose health, submit/show/list/cancel plus scoped worker/operator claim/heartbeat/proposal/kill/reconcile operations. Public/admin client scope is only health + submit/read/list/cancel. Bearer credentials originate from root/operator-provisioned no-follow 0600 files, compare constant-time, are scope mapped, and never appear in logs. Mutations require idempotency and correlation IDs; requests are <=1 MiB, unknown JSON fails, list pages/cursors/projections are bounded, and tokens/query/body/settings are redacted. TCP/non-loopback listening and execution endpoints are absent.
11. **Evidence.** Unit contract/state/migration/service/API tests prove closed validation and transitions. A real disposable PostgreSQL 15+ group proves duplicate intake, competing claim, 20/10/1 capacity, late-fence rejection, retry-to-dead, supersession, trusted budget/WIP stop, kill retention, and two-process kill/restart/reclaim/reconcile. Factory boundary is added to M2 architecture model/diagrams and README. Final full verifier and independent code/test/security/data/release reviews are all bound to the same final fingerprint.

## Non-goals / forbidden cuts

- No GitHub Action, root package marker, provider adapter, model execution, workspace/secret broker, systemd unit or activation, repository command, GitHub fetch/push/PR/merge, connector, deployment/release, or production mutation.
- No `baby-bot` or Telegram modification, network exposure, token read/rotation, or adapter activation. Its later client may consume only the frozen local public/admin API contract.
- No factory claim of Trust CI authority, signed attestation/approval production, or access to trust keys, credentials, policies, holdout, or database state.
- No raw prompts, chain-of-thought, native provider streams, secrets, or unbounded stdout/stderr bodies persisted in factory state.
- No mocked substitute for PostgreSQL lease/fencing/capacity/restart testing; no down migration or audit deletion as rollback.

## Critical vertical delivery sequence

1. **Gate and freeze:** correct the route-base binding, complete the typed M4 change spec, record exact M1/M2/M3 handoff digests and M0-observation/exception decision, approve factory-only disposable DB/role/migration recovery design.
2. **Contracts first:** create isolated package, closed dataclasses/enums/canonical digest/idempotency functions, and red tests for invalid/unknown/stale/excessive intake.
3. **State policy:** add exhaustive state-pair and failure-class tests, then deterministic transition/retry authorization with no provider-directed control.
4. **Migration foundation:** implement immutable migration discovery/checksums/advisory lock and three factory-only migrations with database constraints and role separation tests.
5. **Intake vertical:** implement transactional identity lock, immutable accepted intent, duplicate return, stale supersession, append-only task event/audit, and bounded task lookup/listing; prove against disposable PostgreSQL.
6. **Scheduling vertical:** add `SKIP LOCKED` claim, monotonic fencing, heartbeats/proposals/releases, capacity allocations/counters, and real concurrent claim/late-worker rejection tests.
7. **Control/recovery vertical:** add typed retry/dead-letter, reservations/usage/WIP, kill switches, hash-chained audit permissions, and bounded idempotent reconciliation; run the process-kill/restart drill.
8. **Operator boundary:** add no-follow settings, scoped Unix-socket API/CLI, OpenAPI contract, auth/redaction/request-bound/idempotency/correlation tests, and no execution/network endpoint tests.
9. **Product integration:** update executable architecture/diagrams, verifier/installer discovery, README stack graph/current state, rollout/forward-recovery docs, and preserve M5 absence.
10. **Exit evidence:** run the real PostgreSQL exit suite once, then exactly one final `python3 scripts/grok_verify.py --mode pr`; dispatch all five route-selected reviews on that fingerprint. Any product repair restarts final verification and affected reviews.

## Deadline-aware plan and stop line

The next deadline is Sep 8 00:00 UTC+3. The safe target is M4 source readiness only. Do not borrow time by starting M5 or integrating the bot. If the base-binding/design or disposable-PostgreSQL migration gate is not resolved early, stop before migrations/API; claiming M4 completion without the real PostgreSQL and exact-fingerprint review gates is invalid. External PR/merge remains separately delegated and requires the App-owned policy-epoch check on the final head; this route authorizes neither external writes nor production action.
