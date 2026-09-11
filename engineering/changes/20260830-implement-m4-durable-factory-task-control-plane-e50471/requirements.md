# Requirements — M4 Durable Factory Task Control Plane

## Acceptance criteria

- [ ] AC-001: Closed versioned intake validates exact M1 spec, M2 architecture, M3 governance, base SHA, policy, source, route/change, acceptance IDs, M0 observation, and hard ceilings; malformed or mismatched input fails closed.
- [ ] AC-002: Identical active intake returns one task; a changed source/base/spec/architecture/governance/policy atomically supersedes older nonterminal work without rewriting accepted intent.
- [ ] AC-003: Factory-only checksum-locked migrations create immutable intent, task/event/audit, run/attempt/fence/capacity, budget/usage/kill, and reconciliation state without accessing `trust_ci.*`.
- [ ] AC-004: PostgreSQL `SKIP LOCKED` claim and monotonic fences ensure one live lease owner and reject all late/replayed mutations after expiry or reclaim.
- [ ] AC-005: Database transactions enforce at most 20 global readers, 10 readers per repository, and one live application writer.
- [ ] AC-006: Only typed infrastructure failures retry; initial attempt plus at most two retries is allowed, then the task becomes `dead`.
- [ ] AC-007: Four-hour, USD 25, token, output, event, and repair-capacity limits fail closed when reservation, price, or usage evidence is missing.
- [ ] AC-008: Global/repository kill switches stop new claims without deleting evidence; append-only audit records every actor and transition.
- [ ] AC-009: Reconciliation is restart-safe, idempotent, limited to 100 ordered candidates and a five-second statement timeout, and repairs leases/allocations/deadlines/accounting/stale inputs once.
- [ ] AC-010: The scoped Unix-socket API and CLI provide health, submit, show, list, cancel, claim, heartbeat, proposal, kill, and reconcile boundaries with constant-time bearer authentication, idempotency, correlation, bounds, redaction, and server-side scopes.
- [ ] AC-011: No API, credential, dependency, edge, or database access enables provider execution, Git/GitHub write, systemd, deployment, Trust CI authority, or production mutation.
- [ ] AC-012: Real disposable PostgreSQL tests prove duplicate intake, competing claims, capacity, fencing, retries/dead-letter, supersession, budgets/WIP, kill retention, restart reclaim, and reconciliation.
- [ ] AC-013: Architecture models, generated diagrams, installer/verifier integration, README, release, and rollback records match the final M4 tree.
- [ ] AC-014: Final verification and code, test, security, data, and release reviews bind to the same product fingerprint before the M4 pull request is eligible for external Trust CI.

## Failure and edge cases

- Unknown fields/versions, noncanonical identifiers, dirty SHAs, stale observations, mismatched digests, oversized bodies, stale fences, accounting gaps, active kill switches, unsupported capabilities, and unauthorized cross-repository access fail closed.
- Cancellation, supersession, retry, dead-letter, and operator release are idempotent and evidence-preserving.
- PostgreSQL/process restart leaves committed state authoritative; in-memory state never owns correctness.
- After durable intake, migrations are forward-only: stop claims, retain evidence, restore into a separate database if needed, or add migration `004+`.

## Non-functional requirements

- Security: least privilege, separate factory/trust domains, no secret inheritance, bounded/redacted storage, no self-approval, and independent security review.
- Reliability: database-enforced idempotency, leases, fences, capacity, budgets, audit, and reconciliation.
- Performance: bounded queries/pages/requests, five-second statement timeout, stable lock order, and indexes supporting intake, claim, lease expiry, and reconciliation.
- Observability: bounded metrics for intake, queue age, transitions, capacity, budgets, lease expiry/reclaim, fence rejects, dead letters, kills, reconciliation, and authorization failures without secrets or reasoning content.
- Schedule: follow `schedule.md`; the complete M0–M9 program has a superseding hard deadline of **2026-09-08 00:00 UTC+3**, with feature freeze at 2026-09-07 20:00 and the last four hours reserved for exact-SHA gates, receipts, documentation parity, and recovery evidence. The earlier 2026-09-15 deadline remains only as superseded history.
- Schedule integrity: the deadline cannot override exact-SHA Trust CI, signed approvals, sequential integration, real PostgreSQL/security/review gates, the M8 evidence cohort, or M9 recovery proof. M8 promotion and an M9 completion claim are permitted only after all applicable gates pass; otherwise report the exact blocker.

## Open gates

- PR #16: exact head `5b2a259be0180388d2648c0f535a2469ea91196e` passed `adaptive-trust-ci/verified@06ecf1c875bc`, but remains to be merged/integrated into M2 with the required signed scope.
- PR #10: fresh exact-head Trust CI and external exact-SHA `governance` approval after PR #16 integration.
- PR #11: external exact-SHA `database` and `governance` approvals.
- Fresh M4 route/base fingerprint on the accepted M3 head.
- Separate approval for any non-disposable migration, external write, or production action.
