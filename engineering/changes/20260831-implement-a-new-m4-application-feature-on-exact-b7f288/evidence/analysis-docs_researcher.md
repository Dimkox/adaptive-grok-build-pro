# Documentation, contract, and handoff analysis — M4 control plane

**Route:** `b7f288f1e81e`
**Active change:** `20260831-implement-a-new-m4-application-feature-on-exact-b7f288`
**Mode:** repository-local analysis; only this workflow-evidence report was written.

## Current authoritative baseline

- The actual M4 source base is accepted M3 merge `67714a1f1b87effcfabe55d5ca2770d0a68d17c1` (`Merge pull request #11 from Dimkox/milestone/m3-controlled-knowledge-debt`). It follows the accepted-M2/M3 restack lineage: accepted M2 `022411b05924618cfde0cb97b8c8aff4955e6013`, M3 restack merge `f998ed28efd928ae0627a9e690029bb75e4264db`, and M3 restack closeout `1e73ff9…`.
- `DARK_FACTORY_ROADMAP.md` is the program backlog; `docs/superpowers/specs/2026-08-26-model-agnostic-autonomous-factory-design.md` defines the M4 boundary; `docs/superpowers/plans/2026-08-28-m4-durable-factory-control-plane.md` gives the exact planned package/contracts/test ordering. The active route and active M4 package outrank historical planning package status.
- M4 is an isolated **local control plane**, not M5 execution or M7 delivery: no provider/repository command, workspace/broker, systemd activation, push/PR/merge/release/deploy/connector, bot change, production mutation, GitHub intake fetch, or Trust-CI authority. PostgreSQL `factory.*` is the only M4 operational truth; `trust_ci.*`, its jobs, migrations, credentials, keys, policy, holdout, App identity, approvals, and attestations are prohibited inputs/outputs.
- The route has active `scope_and_design_approval` and `migration_or_external_write_approval` gates. A disposable local PostgreSQL test database may be exercised only within the documented test scope; no production or external database/write is implied.

## Exact M1/M2/M3 handoff contract

M4 must consume frozen, versioned artifacts; it must not reconstruct authority from Markdown, old receipts, route JSON, or repository claims.

| Layer | Consumer contract / repository source | M4 requirement |
| --- | --- | --- |
| M1 | `schemas/change-spec.schema.json`, `.grok-stack/adaptive_grok/spec.py`, `scripts/grok_spec.py` | Valid canonical M1 spec digest and stable acceptance IDs. The active M4 package’s generated `change-spec.yaml` is currently placeholder/`UNKNOWN` content and is not a frozen intake specimen. |
| M2 | `architecture/system.yaml`, `architecture/rules.yaml`, architecture schemas/CLI/fitness; plan-defined `ArchitectureHandoffV1` with contract version, architecture digest, architecture-evidence digest, exact base SHA, exact head SHA | Validate the closed v1 shape and recompute/compare trusted evidence; architecture rules/diagrams must model the new factory boundary only after the factory source exists. |
| M3 | `governance/` registries, governance schemas/CLI, `schemas/governance-handoff-v1.schema.json` | `GovernanceHandoffV1` is exactly six fields: contract version, governance digest, governance-evidence digest, architecture digest, exact base SHA, exact head SHA. It must bind the same architecture digest and compatible exact SHA pair as M2 evidence. |
| M0 | deployed App-owned authority observation | Intake needs a fresh observation (plan: at most 300 seconds old) or a named, issuer/scope/expiry-bounded bootstrap exception. Local receipts cannot substitute for it. |

**Required scope/design ruling:** distinguish the M4 *implementation route base* (`67714a1…`) from the M1/M2/M3 handoff exact base/head values that are produced by their own clean exact-state tools. Do not hard-code historical `f998ed…`, `1e73ff…`, `022411b…`, or `67714a1…` as a fabricated current intake handoff. Record the selected clean M1/M2/M3 handoff artifacts/digests and their cross-SHA mapping before enabling intake; failure/mismatch must reject intake. This resolves the otherwise ambiguous phrase “exact base” without weakening any frozen contract.

## M4 documentation and contract obligations

The active package is a draft shell. Before implementation closure, it must replace `UNKNOWN`/empty typed-spec fields and describe these acceptance boundaries:

1. Closed immutable `TaskIntakeV1`, accepted intent/task/run/attempt/lease projections, canonical SHA-256 JSON and idempotency key. Reject unknown fields/versions, invalid/dirty SHA/digest, unpinned authority, non-NFC/out-of-bound values, unsorted duplicate acceptance IDs, inconsistent M2/M3/M0 bindings, and excessive limits.
2. Factory-only schema/migrations: contiguous immutable checksums (`001` intent/task/event/audit, `002` run/attempt/fence/capacity, `003` budgets/usage/kills/reconciliation), factory advisory lock, least-privilege roles, foreign keys and database constraints. No `trust_ci` table/role/migration reuse.
3. State matrix: normal `inbox → triaged → waiting_design_approval → queued → leased → analyzing → implementing → verifying → reviewing → ready_for_human`; exceptional `retry`, `needs_human`, `dead`, `cancelled`, `superseded`; future `pr_open`/`merged`/delivery values rejected. Provider text never selects state/failure/budget/capability.
4. Transactional idempotent intake/supersession, `FOR UPDATE SKIP LOCKED` lease claims, monotonic fencing on every mutable proposal, database-enforced capacity (20 global readers, 10/repository readers, one application writer), typed retry only (initial + at most two infrastructure retries), dead letter, reservation/usage fail-closed behavior, global/repository kills retaining evidence, hash-chained append-only audit, and bounded restart-safe reconciliation.
5. Versioned local Unix-socket API and CLI. Public/admin `/v1` is health + submit/show/list/cancel; separately scoped worker/operator endpoints are claim/heartbeat/proposal/kill/reconcile. Default socket is operator-owned `0660`; credentials are no-follow regular `0600` token files, constant-time compared, scope mapped, redacted, request bodies ≤1 MiB, unknown JSON rejected. No TCP/non-loopback or execution/external-write endpoint.
6. `factory/README.md`, `factory/contracts/openapi/factory-control.v1.json`, `.env.example` with dummy placeholders, and `compose.yaml` using environment substitution must document local-only operation, recovery, limits, and non-capabilities. The service is a nested package (Python ≥3.11; FastAPI 0.128.2; Uvicorn 0.48.0; psycopg 3.3.4; PostgreSQL 15+); no root packaging marker.

## Calendar deadline / numerical limits

No repository-local calendar due date for M4 was found. The operative “deadline” is a **per-task calendar timestamp**: accepted task wall time is at most **four hours / 14,400 seconds** from acceptance, aggregates across attempts/repairs, and lease expiry may not exceed it. It must be enforced/recorded in durable state using trusted database time; deadline exhaustion stops/escalates work and retains audit evidence.

Other fixed values to retain in documentation/tests: cost ≤USD 25 / 25,000,000 micros, tokens ≤2,000,000, output ≤10MB, events ≤100,000, lease 30–300 seconds, reconciliation ≤100 ordered candidates with 5-second statement timeout, retries initial + two, semantic-repair reservation 1–3 (not executed in M4). No product calendar release deadline should be invented from these runtime ceilings.

## PostgreSQL test, rollout, rollback, and observability evidence

- M4 exit evidence must use only `FACTORY_TEST_DATABASE_URL` and a disposable factory database/schema/roles. Real PostgreSQL—not a mock—must prove duplicate intake, concurrent claims, 20/10/1 capacity, fence rejection, retry/dead-letter, stale supersession, WIP/budget stops, kill retention, restart/reclaim, and idempotent reconciliation. Include bounded restart-probe results and migration checksums/version but no connection string/credential.
- Final local sequence: task-focused RED/GREEN tests; once after store completion, real PostgreSQL cohort and restart probe; after the last product change one `python3 scripts/grok_verify.py --mode pr`; then code/test/security/data/release reviews and receipts against one final fingerprint. Any code/doc product change after receipts invalidates them.
- Rollout is source/local/disposable only: back up named factory schema, migration status/apply under advisory lock, manually start API, synthetic intake/claim/heartbeat/release/kill/restart/reconcile. Before first intake only an explicitly named disposable factory schema may be removed. After intake: kill switch/stop claims/preserve audit, restore into a separate database for validation or use `004+` forward fix; never down-migrate/delete evidence or touch `trust_ci.*`.
- Document bounded low-cardinality signals for intake/duplicate/rejection, task state/queue age, active leases/capacity, reclaims/fence rejection, retry/dead, kill, source supersession, reservation/usage/exhaustion, reconciliation, API auth failures. Do not include task IDs, raw bodies/prompts, output streams, credentials, or chain-of-thought in telemetry/logs.

## README, roadmap, and historical-package corrections

1. **Root README must change only when factory source becomes part of the tree.** Then update Current state/map/stack graph to introduce `factory/` as a local source-only control plane with isolated PostgreSQL and Unix-socket admin boundary; state M5 execution and all external writes remain absent; preserve VERSION `2.0.12` unless separately approved and retain complete K16 `---` graph edges. Do not claim M4 merged/deployed/authoritative before external exact-SHA evidence.
2. **Roadmap status is stale.** Its M3 paragraph still says final verifier/reviews, PR delivery, external Trust CI, signed scopes, and merge are pending, while accepted M3 now exists at `67714a1…`. Update M3 only to the accepted source fact supported by current history; mark M4 as the active implementation branch/package but do not check M4 work/exit items until real evidence exists.
3. **Old package is historical only:** `engineering/changes/20260826-model-agnostic-autonomous-factory-355689/` points at M3 heads `73a45d1…`/`e7c903d…`, states M3 final gates are pending, and names obsolete M4 evidence path `engineering/changes/20260826-model-agnostic-autonomous-factory-355689/evidence/...`. Preserve its original claims as historical design/evidence, but add a short supersession/status note: M3 is accepted at `67714a1…`; this active package is the M4 evidence destination. Do not rewrite old exact receipts/handoffs as if they prove the new branch.
4. The active package’s Markdown and typed spec must name `67714a1…` as M4 source base, current handoff derivation requirements, local/no-network scope, migration/recovery design, and no-external-write boundary. Its final release plan must still require PR-only delivery and a fresh App-owned check for the exact final M4 PR head.

No upstream research was required; the accepted M3 SHA, canonical plan/design, existing handoff schemas, README, roadmap, and historical package are all repository-local.
