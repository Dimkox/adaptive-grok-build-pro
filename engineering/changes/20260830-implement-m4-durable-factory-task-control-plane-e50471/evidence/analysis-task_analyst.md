# Task analysis — M4 Durable Factory Task Control Plane

Route: `e50471553166`  
Active change: `20260830-implement-m4-durable-factory-task-control-plane-e50471`  
Analysis mode: repository-only, read-only except for this report.

## Sources and current state

Primary design authority is `DARK_FACTORY_ROADMAP.md` (§§5–7 and M4), with the detailed approved implementation plan at `docs/superpowers/plans/2026-08-28-m4-durable-factory-control-plane.md` on ref `feature/model-agnostic-factory` (planning commit `bc5ef65`). The route base is `1c062998` (`origin/main`).

The product problem is not a CI queue: it is the absence of a durable, operator-controlled factory scheduler that can survive an interactive session while preventing duplicate, stale, over-budget, or concurrent work from flooding human review. Current routed-base behavior has M1 typed change specs only; it has no `factory/` package, `factory.*` PostgreSQL schema, factory task/run/attempt model, factory API/CLI, factory migrations, or factory tests. `trust-ci/` has a distinct durable verification queue, but the roadmap explicitly forbids using `trust_ci.*` or `trust_ci_jobs` as the factory queue.

### Blocking prerequisite fact

The detailed M4 plan requires an exact reviewed M3 head plus valid frozen M1, M2, and M3 handoffs before intake. `1c062998` does **not** contain the M2 architecture or M3 governance files/interfaces (`architecture/system.yaml`, `architecture/rules.yaml`, `.grok-stack/adaptive_grok/architecture.py`, `.grok-stack/adaptive_grok/governance.py`, or `GovernanceHandoffV1`). Those exist only on divergent local planning/stack refs, not the route base. M4 cannot truthfully validate or consume interfaces absent from its chosen base.

This is a scope/design gate, not an implementation detail: choose and record the exact reviewed M3 stack base (and merge/stack strategy), or explicitly approve a versioned compatibility handoff implementation in this M4 change. Do not silently invent replacement M2/M3 contracts.

## Observable outcome

An authenticated local caller can submit a closed, immutable, digest-bound task intake and receive one durable factory task. The control plane records every transition and actor; safely schedules bounded read/write work; rejects stale lease holders; pauses safely under capacity, budgets, or kill switches; and recovers after a worker/process loss. It is source-level control only: no provider, repository, GitHub, Trust-CI, deployment, or production side effect occurs.

## Acceptance criteria recovered from the design/plan

1. A standalone nested `factory/` Python package (no root packaging marker) owns only a `factory` PostgreSQL schema/database and has no Trust CI state, credential, policy, holdout, approval, or App-key access.
2. Closed immutable contracts exist for `TaskIntakeV1`, M2 `ArchitectureHandoffV1`, M3 `GovernanceHandoffV1`, limits, accepted intent, actor, state/failure enum, lease grant, and canonical SHA-256 JSON digests. Unknown fields, unsupported versions, invalid/non-NFC/bounds-violating values, dirty SHAs, mismatched M2/M3/base/head digests, stale M0 observation (>300 seconds), duplicate/unsorted acceptance IDs, and ceilings above policy defaults fail closed.
3. Intake requires a frozen valid M1 spec digest, exact base SHA, M2/M3 handoffs, policy digest, a current M0-authority observation (or a named recorded bootstrap exception), and immutable caller-provided GitHub-issue projection data; M4 must not contact GitHub.
4. The idempotency key binds source identity/digest, repository, base SHA, spec, M2/M3, and policy. Repeated identical intake returns the same active task. Changed source/base/spec/architecture/governance/policy supersedes prior non-terminal work rather than mutating accepted intent.
5. State transitions are exhaustive and deterministic: `inbox`, `triaged`, `waiting_design_approval`, `queued`, `leased`, `analyzing`, `implementing`, `verifying`, `reviewing`, `ready_for_human`, plus `retry`, `needs_human`, `dead`, `cancelled`, `superseded`. `pr_open`, `merged`, and delivery states are rejected future values. Only authenticated control-plane commands choose transitions; provider output cannot choose state/retry/capability. Terminal semantics and the persisted operator decision required for `needs_human -> queued` are enforced.
6. Packaged, contiguous, checksum-immutable, factory-only migrations create durable accepted intents/tasks/events/audit, runs/attempts/fence sequences/capacity, budgets/usage/kills/reconciliation, with foreign keys and database constraints. Migration application uses a factory advisory lock and never accesses Trust CI migrations.
7. PostgreSQL transactional claim uses `FOR UPDATE SKIP LOCKED`; two workers cannot own a live lease. Heartbeats/releases/proposals verify task/run/packet digest/owner/current state/deadline/budget/idempotency and a monotonic fence in one transaction. A late lease holder cannot heartbeat or commit after reclaim.
8. Capacity is database-enforced: at most 20 global readers, 10 readers per repository, and one live application writer. Work is refused/paused at WIP limits.
9. Retry is only for closed infrastructure classes. Initial attempt plus at most two retries is allowed; a third infrastructure failure reaches `dead`. Validation, auth, policy, stale digest/SHA, budget, security, protocol, unsupported capability, and provider-quality failures never become implicit retries.
10. Enforce maximum 4-hour task wall time, USD 25 (25,000,000 micros) aggregate reservation, 2,000,000 tokens, bounded output/events, and reserved semantic-repair capacity 1–3 (not executed in M4). Missing pricing/usage/accounting fails closed, never as zero cost.
11. Authenticated global and per-repository kill switches block new claims without deleting or rewriting evidence. Append-only, hash-chained audit records capture bounded actor/action/resource/reason/metadata; runtime roles cannot update/delete them.
12. Reconciliation is restart-safe, idempotent, cursor-bounded (100 candidates), statement-timeout-bounded (5 seconds), and repairs expired leases, orphan allocations, deadlines, accounting blocks, stale inputs, and incomplete terminal projections without double counters/events.
13. Local authenticated API/CLI has health, submit, show, list, cancel, claims, heartbeat, proposal, kill, and reconcile boundaries. Its public/admin subset is versioned (`/v1`) and contains only health plus task submit/status/list/cancel. Mutating calls need scoped constant-time bearer auth, idempotency and correlation IDs; requests are <=1 MiB; unknown JSON is rejected; projections/cursors are bounded; tokens, bodies, credentials, and query strings are redacted. Default transport is an operator-created `0660` Unix socket; TCP/non-loopback exposure is absent.
14. The later `baby-bot` client can receive only submit/read/list/cancel scopes. M4 does not edit, restart, deploy, or authenticate Telegram/baby-bot; no bot token is read, rotated, placed in fixtures, or logged.
15. Real disposable PostgreSQL tests prove duplicate intake, concurrent claims, 20/10/1 capacity, fencing, retry/dead-letter, stale supersession, budget/WIP stopping, kill retention, restart/reclaim, and reconciliation. Unit/contract/migration/API tests and root architecture/structure/installer checks also pass. A mock is insufficient for the durable lease/restart exit gate.
16. Architecture model/diagrams and README represent a source-only local factory control boundary, including its isolated database and Unix-socket admin edge, with no execution/publication/Trust-CI edge. Final evidence is bound to one post-change fingerprint and receives route-selected code, test, security, data, and release review.

## Constraints and non-goals

- No GitHub Actions, Dependabot workflow, root `pyproject.toml`/`requirements.txt`/`setup.py`, or reuse of `trust_ci.*`.
- No provider/model/repository command, workspace execution/isolation, GitHub fetch/push/PR/merge, connector, note execution, systemd unit/activation, deployment/release, production write, or autonomous external action. Those begin at M5+ or an operator-owned later integration.
- No Trust CI authority publication, attestation/approval key access, or credentials crossing into factory. Trust CI verifies; factory controls task state.
- No raw prompts, chain of thought, provider streams, unbounded log bodies, secrets, or arbitrary stdout/stderr in durable state.
- Durable migrations are forward-only after first intake: kill/stop claims and preserve audit/evidence; restore to a separate database or forward-fix with a new migration, never down-migrate/delete history.
- Scope has named human gates: `scope_and_design_approval`, `migration_or_external_write_approval`, and `production_action_approval`. This task permits no external/prod mutation, but a disposable test database must be operator-provided and its migration/recovery design approved.

## Risks and mitigations

| Risk | Severity | Required mitigation/evidence |
| --- | --- | --- |
| Wrong stack base / invented prerequisite handoff | Blocker | Record exact M3 base and frozen M1/M2/M3 handoff digests before code; fail intake otherwise. |
| Concurrent or zombie worker mutates task | Critical | PostgreSQL `SKIP LOCKED`, DB capacity constraints, monotonic fences, real concurrency/late-result drill. |
| Duplicate/stale intake causes duplicate PR pressure | High | Immutable canonical idempotency; supersession transaction and tests. |
| Budget/capacity bypass or accounting omission | High | Reservations/usage fail closed, limits in transaction, bounded reconciliation, real integration tests. |
| Factory becomes a trust/execution backdoor | Critical | Separate DB/roles/packages/credentials; no external endpoints; architecture/security review. |
| Local socket/token exposure | High | Root-provisioned no-follow 0600 token files, scoped constant-time auth, 0660 socket, redaction/bounds tests. |
| Migration/audit loss | High | Immutable checksums/advisory lock, append-only permissions, forward recovery, disposable backup/restart drill. |
| Plan contains a later bot integration dependency | High | Keep `/home/pall/baby-bot` untouched; token rotation/log redaction are post-M4 human gates. |

## Ambiguous product decisions requiring a recorded ruling

1. **Prerequisite source:** which exact reviewed M3 commit/PR is M4 stacked on, given the routed base lacks M2/M3? This must be resolved before contract implementation.
2. **M0 exception:** the plan requires an M0 observation fresh within 300 seconds. If live M0 authority is unavailable, name the allowed bootstrap exception, issuer, scope, and expiry; do not silently waive it.
3. **Operator policy values:** the plan gives maximum ceilings but needs durable policy ownership for per-repository WIP/open-PR limits, lease duration, retention, token/cost pricing source, and kill-switch operator identity.
4. **Database provisioning:** identify only the disposable test/staging database and factory runtime role model; no existing trust or production database/credentials may be reused.
5. **API caller boundary:** confirm whether the public/admin five-operation contract is the only M4 client contract. `baby-bot` integration and any Telegram authorization remain explicitly deferred.

## Recommended bounded delivery sequence

Resolve the stack-base/handoff gate; freeze the typed contracts and state matrix; add factory-only migrations and transactional store; prove durable lifecycle with one real disposable PostgreSQL run; then add the Unix-socket API/CLI and architecture/root integration. Finish with exactly one final verifier and the route-required independent reviews on the final fingerprint. Do not start M5 execution or the bot integration in this change.
