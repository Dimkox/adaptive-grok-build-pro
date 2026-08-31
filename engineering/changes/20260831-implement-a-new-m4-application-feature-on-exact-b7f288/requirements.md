# Requirements — M4 Durable Factory Task Control Plane

## Acceptance criteria

- [ ] AC-001 closed versioned intake validates frozen M1 spec, M2 architecture, M3 governance, exact source/base, policy, route/change, acceptance IDs, M0 observation/exception and hard ceilings.
- [ ] AC-002 duplicate active intake returns one task; changed source or frozen authority atomically supersedes eligible nonterminal work without rewriting accepted intent.
- [ ] AC-003 factory-only contiguous checksum migrations create isolated durable state and roles without `trust_ci` access.
- [ ] AC-004 `SKIP LOCKED` claims and monotonic fences reject expired, reclaimed, replayed and conflicting worker mutations.
- [ ] AC-005 database transactions enforce at most 20 global readers, 10 readers/repository and one live writer.
- [ ] AC-006 only closed infrastructure failures retry; attempt three becomes `dead`.
- [ ] AC-007 14,400-second, USD 25, token, output, event and repair budgets fail closed on missing accounting.
- [ ] AC-008 global/repository kills block new claims while append-only hash-chained audit retains evidence.
- [ ] AC-009 reconciliation is restart-safe, idempotent, ordered, at most 100 candidates and five seconds.
- [ ] AC-010 scoped authenticated Unix-socket API/CLI provide health, submit, show/list, cancel, claim, heartbeat, proposal/release, kill and reconcile with bounds, idempotency, correlation and redaction.
- [ ] AC-011 no product path can execute a provider/repository command, write Git/GitHub/external/production state, activate systemd, or claim Trust CI authority.
- [ ] AC-012 real disposable PostgreSQL proves concurrency, capacity, fencing, retries, budgets, kill, restart and reconciliation.
- [ ] AC-013 architecture/diagrams, installer/verifier, README, release and rollback match the final tree.
- [ ] AC-014 final verification plus code/test/security/data/release reviews bind one final fingerprint.

## Failure and edge cases

Unknown fields/versions, invalid SHA/digest/NFC/bounds, unsorted acceptance IDs, stale authority, mismatched producer handoffs, stale fences, kill switches, missing price/usage and unauthorized repository access fail closed. Cancellation, supersession, release and repair are evidence-preserving and idempotent. Durable migrations are forward-only after intake.

## Governance and non-functional constraints

Canonical governance JSON remains independently reviewed authority. Factory records frozen producer handoffs but cannot activate governance or infer authority from Markdown, local receipts or caller claims. PostgreSQL is operational truth; fixed lock order, parameterized SQL, bounded pages/queries, low-cardinality redacted signals and separate least-privilege roles are mandatory.
