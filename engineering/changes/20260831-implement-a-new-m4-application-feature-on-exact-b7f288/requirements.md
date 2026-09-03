# Requirements — M4 Durable Factory Task Control Plane

## Non-authoritative decomposed requirements checklist

The canonical typed acceptance criteria remain `AC-001` through `AC-004` in `change-spec.yaml`. The `RQ-*` items below decompose those criteria for implementation tracking; they do not create, replace or extend typed acceptance authority.

- [ ] RQ-001 closed versioned intake validates frozen M1 spec, M2 architecture, M3 governance, exact source/base, policy, route/change, acceptance IDs, M0 observation/exception and hard ceilings.
- [ ] RQ-002 semantic duplicate intake returns one task across new request IDs and refreshed equivalent M0 proof; command replay binds one request ID to one full body/result, while changed semantic work atomically supersedes eligible nonterminal work without rewriting accepted intent.
- [x] RQ-003 factory-only contiguous checksum migrations create isolated durable state and roles without `trust_ci` access.
- [x] RQ-004 `SKIP LOCKED` claims and monotonic fences reject expired, reclaimed, replayed and conflicting worker mutations.
- [x] RQ-005 database transactions enforce at most 20 global readers, 10 readers/repository and one live writer.
- [x] RQ-006 only closed infrastructure failures retry; each frozen accepted limit 0..2 is persisted and permits exactly the initial attempt plus that many retries before `dead`.
- [x] RQ-007 14,400-second, USD 25, token, output, event and repair budgets fail closed on missing or quarantined accounting.
- [x] RQ-008 global/repository kills block new claims while append-only hash-chained audit retains evidence.
- [ ] RQ-009 reconciliation is restart-safe, idempotent, ordered, at most 100 candidates and five seconds for the whole operation.
- [ ] RQ-010 scoped authenticated Unix-socket API/CLI provide health, submit, show/list, cancel, claim, heartbeat, proposal/release, kill and reconcile with bounds, idempotency, correlation and redaction.
- [x] RQ-011 no product path can execute a provider/repository command, write Git/GitHub/external/production state, activate systemd, or claim Trust CI authority.
- [x] RQ-012 real disposable PostgreSQL 17 proves concurrency, capacity, fencing, accepted 0/1/2 retry limits, budgets, kill, actual restart and reconciliation.
- [ ] RQ-013 architecture/diagrams, installer/verifier, README, release and rollback match the final tree.
- [ ] RQ-014 final verification plus fresh code/test/security/data/release reviews and receipts still must bind the current repair tree to one final fingerprint; no review acceptance, external Trust CI result or delivery is claimed.

## Crosswalk to typed acceptance

| Typed authority item | Decomposed checklist |
| --- | --- |
| `AC-001` | `RQ-001`, `RQ-002` |
| `AC-002` | `RQ-004` through `RQ-009`, `RQ-012` |
| `AC-003` | `RQ-010`, `RQ-011` |
| `AC-004` | `RQ-013`, `RQ-014` |
| `INV-001`, `FORBID-002` | `RQ-003` |
| `INV-002` | `RQ-005` |
| `INV-004` | `RQ-007` |

## Failure and edge cases

Unknown fields/versions, invalid SHA/digest/NFC/bounds, unsorted acceptance IDs, stale authority, mismatched producer handoffs, stale fences, kill switches, missing price/usage and unauthorized repository access fail closed. Cancellation, supersession, release and repair are evidence-preserving and idempotent. Durable migrations are forward-only after intake.

## Governance and non-functional constraints

Canonical governance JSON remains independently reviewed authority. Factory records frozen producer handoffs but cannot activate governance or infer authority from Markdown, local receipts or caller claims. PostgreSQL is operational truth; fixed lock order, parameterized SQL, bounded pages/queries, low-cardinality redacted signals and separate least-privilege roles are mandatory.
