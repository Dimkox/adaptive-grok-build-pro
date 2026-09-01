# Final exact-head code review — M4 durable factory control plane

## Verdict

**PASS**

No Critical or Important correctness, maintainability, or invariant finding remains on the exact reviewed product HEAD. The migration-011 active-generation collision is closed without weakening identity uniqueness, claim fencing, accounting fail-closure, or evidence retention. Prior code-review findings remain closed.

## Review binding

- Route: `b7f288f1e81e`
- Accepted M3 base and exact merge base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Prior reviewed product HEAD: `04261326e177e6d2014a576d3f4a0fb5feab56be`
- Exact reviewed product HEAD: `daa3930cb84ba6547171583e41bcf0dee2ab1314`
- Exact Git tree: `9c93b2ca4fea4f71ab70bbf71bd62ca8df936ad8`
- Collision-fix commit: `d15302f0bf5250cb4c7a3d623ccd56c96acdb16e`
- Focused range: `04261326e177e6d2014a576d3f4a0fb5feab56be..daa3930cb84ba6547171583e41bcf0dee2ab1314`
- Full range inspected with surrounding implementation, contracts, migrations, tests, architecture, and change package: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..daa3930cb84ba6547171583e41bcf0dee2ab1314`
- Exact-head verifier before review-report writes: **PASS**, all 14 gates, created `2026-09-01T22:11:35+00:00`, fingerprint `ad41a13355b097f4be0a3d6c3754b9cc4de8178824e801ac264fad81c852e794`.

## Findings

None.

## Migration 011 collision closure

- `tasks_one_active_identity` continues to exclude only the four terminal/non-active projections `ready_for_human`, `dead`, `cancelled`, and `superseded`; no uniqueness constraint or claim predicate was weakened.
- Migration 011 now sends an unsafe legacy `ready_for_human` task with a newer generation of the same repository/source identity to `superseded/accounting_blocked`. A lone unsafe positive generation, and blocked `queued`/`retry` projections, go to `needs_human/accounting_blocked`.
- The exact repository, source type, source ID, and strictly greater generation predicate makes the branch deterministic. It cannot displace the newer index-active generation or introduce a second active identity.
- The migration changes only task projection fields. It retains accepted intent, runs, attempts, reservations, usage, task events, audit chain, aggregate values, and terminal history; it neither fabricates settlement nor releases capacity/accounting evidence.
- Readiness independently rejects unsafe positive or claimable projections and rejects a superseded accounting projection if its explicit `accounting_blocked` quarantine marker is removed. Claim independently selects only unblocked zero-reservation `queued`/`retry` work.
- The real schema-008 regression uses the exact same source identity for unsafe generation 1 and queued generation 2. It proves atomic application of `009..011`, generation 1 becomes `superseded/accounting_blocked`, generation 2 remains the sole claim target, exact reservation aggregates survive, readiness is truthful, owner fault injection fails closed, and migration replay is empty.

Migration 011 was corrected before PR or deployment under the recorded unreleased/disposable-only exception. Migrations 001 through 010 remain unchanged. The documented consequence is appropriate: any undisclosed persistent test database carrying the superseded 011 checksum must be discarded and recreated; checksum history is never overridden.

## Cumulative code-path review

- Intake verifies persisted M0 authority inside the intake transaction, serializes revocation with `FOR SHARE`, binds complete frozen intent, and atomically supersedes eligible active work under a source-identity advisory lock.
- Claims remain database-time `FOR UPDATE SKIP LOCKED` operations with monotonic fences, live allocation proof, deadline/accounting guards, and database-owned 20/10/1 capacity. Worker mutations bind actor, repository, task, run, owner, fence, packet, lease, deadline, and budget state.
- Release, cancellation, supersession, and reconciliation preserve capacity-before-task lock order. Missing or hidden allocation/accounting state fails closed; mandatory cleanup remains idempotent and cannot be rolled back by ordinary event-budget exhaustion.
- Completion requires current-run usage plus task-wide settled reservations and aggregates. Retry remains limited to the closed infrastructure classes and three total attempts.
- Command replay remains actor/action/request bound. Audit v2 binds task/run/correlation and all semantic fields while retaining verification of v1 history.
- API and service boundaries retain closed bounded parsing, repository/scope checks, wildcard-only global controls, constant-time bearer authentication, no-follow private credential loading, cumulative 1 MiB body limits, and Unix-socket-only serving.
- M4 still has no provider execution, shell/repository command, Git/GitHub mutation, TCP listener, deployment, systemd, production-write, or Trust-CI authority path.

## Verification evidence

- Initial `git status --short` was empty; `git rev-parse HEAD` returned the exact reviewed SHA and `git merge-base` matches the accepted M3 base.
- `git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1...daa3930cb84ba6547171583e41bcf0dee2ab1314` — PASS.
- Independent dependency-free contracts/state/migrations/service run — PASS, 24/24 in 0.014s.
- Exact-head verifier receipt — PASS, 14/14: root 488/488, factory unit 24/24, fresh disposable PostgreSQL 63/63, actual restart/reconcile, source stability, architecture, contracts, SQL safety, secret scan, Ruff, Bandit, and governance gates.
- The implementation ledger additionally records the exact schema-008 RED `UniqueViolation`, focused GREEN 1/1 and 2/2 upgrade/bootstrap runs, installer 17/17, full PostgreSQL/restart exit, and root regression on product commit `d15302f`.
- After review execution, HEAD remained `daa3930...`; only route-designated review reports were dirty, with no product, contract, migration, test, architecture, governance, or release file changed.

## Residual boundary

Migration 011 deliberately quarantines rather than settles legacy accounting; any disposition remains a separately reviewed forward recovery. Its owner update runs in the stopped local migration transaction with the existing five-second timeout, so excessive legacy volume fails atomically and remains no-go rather than partially applying.

This PASS is local exact-product-head review evidence only. Writing review reports changes the evidence-tree fingerprint. The coordinator must freeze all five reports, rerun fingerprint-bound verification, record receipts on that final tree, and still obtain the App-owned exact-PR-SHA Trust CI check plus all independently signed scopes before merge.
