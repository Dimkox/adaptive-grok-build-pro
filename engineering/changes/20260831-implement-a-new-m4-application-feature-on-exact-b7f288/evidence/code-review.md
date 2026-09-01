# Final code re-review — M4 durable factory control plane

## Verdict

**PASS**

No Critical or Important findings remain in the exact reviewed tree. CR-004 is closed for both M0 authority forms and both revocation orderings; migration 010, mandatory cleanup and schema-008 upgrade defenses introduce no blocking regression. Prior CR-001 through CR-003 remain closed.

## Review binding

- Route: `b7f288f1e81e`
- Product base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Prior reviewed HEAD: `4230dc8e73bcf4dfcf6c60d294d379d44a30c698`
- Exact reviewed HEAD: `83e6b0d0c29e813932aa29b0d72ac4d85d27df7b`
- Exact merge base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Full range inspected: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..83e6b0d0c29e813932aa29b0d72ac4d85d27df7b`
- Focused residual range inspected: `4230dc8e73bcf4dfcf6c60d294d379d44a30c698..83e6b0d0c29e813932aa29b0d72ac4d85d27df7b`
- Exact-head verifier receipt before this report rewrite: **PASS**, fingerprint `9a9dd64921cc5edf8889330b79732016c0235cc37e4a27c712a05128b3659746`, created `2026-09-01T21:10:24+00:00`. It records factory unit, disposable PostgreSQL/API exit, actual restart/reconciliation and source stability as passing.

## Findings

None.

## CR-004 closure — transaction-serialized M0 revocation

- Forward migration 010 replaces both schema-009 authority validators with fixed-search-path `SECURITY DEFINER` functions whose matching rows are selected `FOR SHARE` (`factory/src/adaptive_factory/resources/010_authority_accounting_and_cleanup.sql:1-31`). `FOR SHARE` conflicts with the `FOR NO KEY UPDATE` row lock taken by a non-key `revoked_at` update, so a successful validation holds revocation behind the intake transaction's commit.
- PUBLIC execution is revoked again and only `factory_runtime` receives EXECUTE (`010_authority_accounting_and_cleanup.sql:33-36`). Repository, full policy, action, expiry, exact-head and non-revoked predicates from migration 009 remain unchanged; the repair strengthens serialization without widening authority.
- The pre-validation regression separately revokes observations and exceptions, then proves intake creates no task (`factory/tests/test_postgres_integration.py:235-257`).
- The post-validation regression pauses immediately after `_verify_m0_authority` returns, starts the revoker on a second connection, proves it remains blocked, then resumes intake and checks intake commit precedes revocation commit. It repeats this for both observation and exception rows and proves later reuse is rejected (`factory/tests/test_postgres_integration.py:259-316`). This directly covers the interleaving missed by the prior advisory-gated test.
- Migration 009 is not rewritten. Migration 010 is contiguous, checksum-bound and forward-only, so already applied schema history remains immutable.

## Migration 010, cleanup and upgrade review

- Migration 010 adds `mandatory_cleanup` with a safe `false` default for historical events. Store event accounting limits ordinary events separately while release, cancellation, supersession and orphan/reconciliation cleanup append one idempotent mandatory fact plus the hash-chained audit even after ordinary budget exhaustion (`factory/src/adaptive_factory/store.py:175-220,294-315,618-643,729-759,1048-1068`).
- Retry does not re-enter an unclaimable loop when no ordinary event capacity remains: it is routed to `needs_human` before run/capacity closure. Exact release command replay still returns the recorded status before fence/state mutation.
- Real PostgreSQL tests exhaust the event budget and prove release/reconcile/cancel close runs and allocations, restore counters, emit cleanup/audit once, and replay without double release (`factory/tests/test_postgres_integration.py:853-955`).
- Migration 010 quarantines schema-008 `queued`/`retry` tasks with unresolved live reservations or nonzero reserved aggregates into `needs_human` with `accounting_blocked`, preserving all reservation evidence (`010_authority_accounting_and_cleanup.sql:41-70`). It neither deletes nor synthesizes accounting evidence.
- Runtime readiness now requires exact schema, capacity agreement and safe claimable accounting. Claim independently excludes blocked/nonzero/live-reservation tasks, so an owner fault or incomplete historical repair remains unclaimable even before readiness is consulted (`factory/src/adaptive_factory/store.py:61-97,492-526`).
- The upgrade regression builds a non-empty schema 008 database, seeds a failed prior attempt plus full live reservation, applies only migrations 009 and 010, and proves quarantine, preserved aggregates/evidence, ready schema 10 and no claim. Owner fault injection back to an unsafe retry projection makes readiness fail and the claim guard still returns no grant (`factory/tests/test_postgres_integration.py:984-1098`).
- A legacy `queued`/`retry` row that was already `accounting_blocked` but has zero counters/reservations is not silently cleared by migration 010: readiness stays no-go until operator recovery. That is a conservative fail-closed upgrade outcome, not an unsafe claim path.

## Prior finding recheck

| Finding | Final result | Evidence |
| --- | --- | --- |
| CR-001: changed frozen authority was collapsed into a subset-key duplicate | **Closed** | Duplicate identity hashes the complete intent; unit and PostgreSQL tests cover exact replay plus changed limit, producer head and evidence supersession (`factory/src/adaptive_factory/contracts.py:267-271`; `factory/tests/test_contracts.py:66-81`; `factory/tests/test_postgres_integration.py:151-178`). |
| CR-002: repository-limited actor could run global reconcile/metrics | **Closed** | Both operations require operator kind plus wildcard repository authority before store access; focused service test proves denial (`factory/src/adaptive_factory/service.py:30-34,148-152`; `factory/tests/test_service.py:85-95`). |
| CR-003: malformed closed API commands escaped as 500/database failures | **Closed** | Closed parsers validate enums, mappings, UUIDs, strict integers, digests, repositories, cursor and bounded reasons; malformed cases return bounded 4xx (`factory/src/adaptive_factory/api.py:66-130,191-440`; `factory/tests/test_api.py:131-159`). |
| CR-004: key-share authority lock allowed post-validation revocation to commit first | **Closed** | Both validators use conflicting `FOR SHARE`; two-connection tests cover before/after validation for both authority forms (`010_authority_accounting_and_cleanup.sql:1-36`; `factory/tests/test_postgres_integration.py:235-316`). |

## Cumulative control-plane review

- Claims remain transactional `FOR UPDATE SKIP LOCKED`, use database time, monotonic fences and database-owned 20/10/1 capacity. Live grant mutations bind task, run, owner, fence, packet, state, allocation, lease and deadline.
- Capacity-before-task lock ordering is consistent across release, cancel, supersede and reconciliation. Missing/hidden allocation state fails fencing/readiness rather than repairing speculatively.
- Durable command replay remains actor/action/request bound and is checked before mutable fence state where exact replay requires it. Empty claims and accounting results remain persisted.
- Accounting limits, cross-attempt reservations and completion fail closed. Migration 010 additionally prevents unsafe historical retry work from becoming claimable after upgrade.
- Audit version 2 binds task, run, correlation, actor, action, resource, reason, timestamp and canonical metadata while retaining verification compatibility for historical version-1 rows.
- API/server remain authenticated UDS-only with bounded bodies, owned no-follow credential ancestry, no access logging and no provider/repository command, Git/GitHub, deployment, systemd, TCP or external-write path.
- Local bootstrap keeps owner/migrator and runtime DSNs distinct, provisions a bounded `NOINHERIT` login and verifies readiness under the effective runtime role.
- Rollback remains evidence-preserving: global kill, stop intake/claims, retain state/audit, restore into a separate comparison database and forward-fix with migration 011+; no destructive down migration is proposed.

## Verification evidence

- `git merge-base <base> HEAD` — exact route base returned.
- `git diff --check <base>..<head>` and current worktree diff check before report rewrite — PASS.
- Reviewer dependency-free contract/state/migration/service suite — PASS, 24/24.
- Reviewer verifier-capability matrix — PASS, 4/4; exact sandbox value skips only the database exit while absent/look-alike values execute and propagate it.
- Exact-head verifier receipt — PASS at fingerprint `9a9dd64921cc5edf8889330b79732016c0235cc37e4a27c712a05128b3659746`.
- Receipt factory exit — PASS, 63/63 against fresh disposable PostgreSQL 17 plus actual restart, one repair, replay no-op, higher fence and late-holder rejection.
- Focused implementation evidence — authority/upgrade/cleanup PostgreSQL cases 5/5, installer 17/17, root suite 488/488, Ruff and architecture gates passed before the exact-head verifier.

## Residual risks

The new `FOR SHARE` lock intentionally makes revocation wait for an already validated intake transaction; the five-second intake lock/statement timeout bounds pathological contention, and operators should treat a timeout as no acceptance. Mandatory cleanup facts may take total event rows above the ordinary task event limit, but they are a separately marked, idempotent and attempt-bounded safety channel required to release capacity and preserve audit. Schema-008 upgrades can conservatively remain not-ready on other pre-existing blocked projections until reviewed recovery; they cannot become claimable through the runtime path.

This report is local exact-head review evidence only. Rewriting it makes the prior verifier receipt stale for the worktree; receipt refresh, the other route-selected reviews, PR delivery, the App-owned exact-SHA check and signed approvals remain separate gates.
