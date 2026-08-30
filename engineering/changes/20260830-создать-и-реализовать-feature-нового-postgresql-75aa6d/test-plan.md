# Test plan — production-only human approvals

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Strict V1 schema, canonical JSON and tamper/key/time/scope matrix | Model/signing unit and contract tests |
| P0 | Webhook merge fact plus GitHub API corroboration and exact artifact attestation | Adapter/runner/provenance tests |
| P0 | Concurrent replay and consume-once have exactly one winner and atomic audit | Real PostgreSQL multi-connection tests |
| P0 | Mirrored migration 004, populated upgrade, roles, restart and restore | Compose migration/role tests |
| P0 | New policy removes interactive PR approval but retains every automatic gate | Disposable PR policy-transition drill |
| P1 | Lost webhook reconciliation, bounded retries and secret-free observability | Worker/API/runbook tests |

## Automated checks

- Unit: strict models, duplicate-key parser, canonical bytes, verifier, policy, transitions and errors.
- Integration: PostgreSQL concurrency/rollback/restart, GitHub fixtures, supply-chain verifier, roles and query plans.
- Contract: OpenAPI, JSON/event schemas, CLI exits and MemoryStore/PostgresStore parity.
- E2E: shadow exact-merged-SHA flow and deny-only consume with mismatch/replay/expiry/rotation cases.
- Static analysis: formatter/linter/type/security, migration mirror/checksum, no Actions/private material.

## Manual checks

- Human creates the no-op/canary envelope outside the agent environment.
- Operator verifies App identity/context, branch protection, backup/restore, kill switch and rollback evidence.
