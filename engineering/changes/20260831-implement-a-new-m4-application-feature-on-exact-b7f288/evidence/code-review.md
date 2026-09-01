# Final code re-review — M4 durable factory control plane

## Verdict

**PASS**

No Critical or Important findings remain at the exact reviewed product HEAD. Forward migration 011 closes the two remaining legacy-accounting recovery gaps without weakening claim, readiness, authority, fencing, command-replay, audit, or capacity contracts. Prior CR-001 through CR-004 remain closed.

## Review binding

- Route: `b7f288f1e81e`
- Product base and exact merge base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Previous reviewed HEAD: `83e6b0d0c29e813932aa29b0d72ac4d85d27df7b`
- Exact reviewed HEAD: `04261326e177e6d2014a576d3f4a0fb5feab56be`
- Focused range inspected: `83e6b0d0c29e813932aa29b0d72ac4d85d27df7b..04261326e177e6d2014a576d3f4a0fb5feab56be`
- Full range and surrounding implementation inspected: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..04261326e177e6d2014a576d3f4a0fb5feab56be`
- Exact-head verifier receipt before this report rewrite: **PASS**, created `2026-09-01T21:45:05+00:00`, tree fingerprint `e7401c598db44069e77259d7e0f4da893e67b89f4778e195af540c3a753e86b0`; all 14 gates passed, including the disposable PostgreSQL exit and source-stability gate.

## Findings

None.

## Migration 011 and readiness invariant

- Migration 011 is a new contiguous forward migration; applied migrations 001 through 010 remain byte-for-byte immutable. Discovery/checksum and installer inventories now require 011.
- A legacy `queued` or `retry` task already marked `accounting_blocked`, including the previously omitted zero-aggregate/no-live-reservation form, is moved to `needs_human`. It cannot poison readiness indefinitely and cannot re-enter claim.
- A legacy `ready_for_human` task is quarantined when it is blocked, carries a nonzero reserved aggregate, or has any live reservation. The migration sets `accounting_blocked=true` and retains costs, token/wall aggregates, reservation rows, run/attempt history, usage observations, audit and timestamps; it neither fabricates settlement nor deletes evidence.
- The store independently treats the same unsafe accounting forms in `queued`, `retry`, and `ready_for_human` as readiness failures. Thus a partially applied/manual regression fails closed even apart from the migration, while the explicit `needs_human` quarantine permits healthy unrelated work to resume.
- Claim remains independently defensive: only `queued`/`retry` are candidates, and blocked, nonzero-reserved, or live-reservation tasks are excluded. Moving an unsafe terminal projection to `needs_human` does not create an execution path or release capacity speculatively.
- The real schema-008 upgrade regression seeds all three historical forms: a retry with live full reservation, a blocked-zero retry, and a `ready_for_human` task with a completed usage fact plus unresolved prior-attempt reservation. Applying only 009/010/011 moves all three to `needs_human`, preserves exact accounting evidence, reports schema 11 ready, denies claim, detects owner-injected retry and human-ready regressions, and proves migration replay is empty.
- Retaining the old `terminal_at` on the quarantined human-ready row is evidence-preserving and has no runtime authority: claim/state selection is based on the current `needs_human` state, and no M4 resume path consumes that timestamp. Recovery remains an operator-reviewed forward repair rather than a destructive rewrite.

## Prior finding recheck

| Finding | Final result | Current contract |
| --- | --- | --- |
| CR-001: subset-key intake replay collapsed changed frozen intent | **Closed** | Duplicate identity includes the complete frozen intent; changed limits, producer head and evidence supersession are rejected while exact replay is stable. |
| CR-002: repository-limited actor could invoke global reconciliation/metrics | **Closed** | Both operations require operator kind and wildcard repository authority before store access. |
| CR-003: malformed closed API commands could escape as 500/database failures | **Closed** | Closed parsers validate enums, mappings, UUIDs, strict integers, digests, repositories, cursors and bounded reasons into bounded 4xx responses. |
| CR-004: authority key-share lock allowed revocation to commit after validation but before intake | **Closed** | Both M0 validators use `FOR SHARE`; two-connection tests cover revoke-before and post-validation blocking for observation and exception forms. |

Migration 011 does not touch any of these code paths, validators, table privileges, API handlers, or command identities.

## Cumulative control-plane review

- Claim remains a database-time, transactional `FOR UPDATE SKIP LOCKED` transition with monotonic fences and database-owned 20/10/1 capacity. Mutations bind task, run, owner, fence, packet, allocation, lease and deadline.
- Release, cancellation, supersession and reconciliation preserve capacity-before-task lock ordering. Missing/hidden allocation or accounting state fails closed rather than being inferred or silently cleared.
- Exact command replay remains actor/action/request bound and precedes mutable fence checks where required. Mandatory cleanup facts are separately marked, idempotent and attempt-bounded, so event-budget exhaustion cannot roll back run/capacity closure.
- Completion requires settled accounting and durable usage. Cross-attempt live reservations cannot be hidden by a successful later attempt; migration 011 extends the same invariant to legacy positive endpoints.
- Audit v2 binds task/run/correlation, actor, action, resource, reason, timestamp and metadata while preserving historical verification. Migration 011 changes projections only and retains the audit chain.
- API/server remain authenticated Unix-socket-only, bounded-body, no-follow credential ancestry, without access logging or provider/repository execution, Git/GitHub, deployment, systemd, TCP or external-write commands.
- Local bootstrap retains separate owner/migrator and runtime identities, and readiness is checked under the effective runtime role at exact schema 11.
- Rollback remains evidence-preserving: enable global kill, stop intake/claims, retain durable state/audit, restore into a separate comparison database, and forward-fix with migration 012+. No destructive down migration is proposed.

## Verification evidence

- Exact `git merge-base` equals the route product base.
- `git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..04261326e177e6d2014a576d3f4a0fb5feab56be` — PASS.
- Reviewer dependency-free contract/state/migration/service suite — PASS, 24/24.
- Focused upgrade/bootstrap PostgreSQL evidence — PASS, 2/2; installer — PASS, 17/17; Ruff — PASS, as recorded in the implementation ledger.
- Fresh disposable PostgreSQL exit — PASS, 63/63, including actual restart, one repair, replay no-op, higher fence and late-holder rejection.
- Full root regression — PASS, 488/488 on product commit `3bbafeb`; exact HEAD `0426132` adds only final verification documentation after that product commit.
- Exact-head local verifier — PASS, 14/14 gates, fingerprint `e7401c598db44069e77259d7e0f4da893e67b89f4778e195af540c3a753e86b0`.

## Residual risks

Migration 011 deliberately quarantines rather than settles historical accounting, so operators still need an evidence-backed forward recovery for affected tasks. The readiness query adds a live-reservation anti-join over the three safety-relevant states; the reservation/task indexes and bounded factory population support it, but production latency should still be observed during rollout. As with migration 010, concurrent operational use must remain stopped during the owner migration transaction.

This report is local exact-head review evidence only. Rewriting it makes the pre-review verifier receipt stale for the worktree. Receipt refresh, the other route-selected reviews, PR delivery, the App-owned exact-SHA Trust CI check and required independently signed approvals remain separate gates.
