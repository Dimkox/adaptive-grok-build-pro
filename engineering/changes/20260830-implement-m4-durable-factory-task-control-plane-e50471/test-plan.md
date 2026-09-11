# Test plan — M4 Durable Factory Task Control Plane

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Two workers race; one lease/fence wins and late owner cannot mutate | Real PostgreSQL concurrency test |
| P0 | Capacity stays at 20 global readers, 10 repository readers, one writer | Real PostgreSQL contention test |
| P0 | Restart/lease expiry reclaims exactly once with a higher fence | Two-process restart probe |
| P0 | Factory roles cannot access Trust CI or update/delete audit | PostgreSQL privilege tests |
| P0 | Auth/scope/resource boundaries reject forged or cross-repository commands | API and store contract tests |
| P1 | Duplicate intake returns one task; changed frozen input supersedes old work | Service plus PostgreSQL tests |
| P1 | Third infrastructure failure dead-letters; non-infrastructure failures do not retry | State/service tests |
| P1 | Missing usage/pricing, budget/WIP, or kill switch stops claims | Service plus PostgreSQL tests |
| P1 | Reconciliation is bounded, idempotent, and repairs no counter twice | PostgreSQL integration tests |
| P1 | OpenAPI/CLI expose no provider, GitHub, systemd, deploy, or production operation | Contract/API tests |

## Automated checks

- Unit: contracts, canonical digests, state matrix, retry policy, settings, service decisions.
- Migration: contiguous names, immutable checksums, factory advisory lock, drift rejection, constraints/index inventory.
- Contract/API: OpenAPI validation, unknown-field/body bounds, token-file/auth/scopes, idempotency/correlation, redaction, pagination.
- Integration: disposable PostgreSQL 15+, concurrent intake/claim/capacity/budget/kill/reconcile and runtime-role permissions.
- Drill: kill lease-holder subprocess, wait to expiry, reclaim with higher fence, reject late result.
- Repository: architecture validate/diagram check, installer/structure tests, factory tests, `git diff --check`.
- Final: exactly one `python3 scripts/grok_verify.py --mode pr` on the final product fingerprint, then route-selected reviews.

## Stop conditions

- Do not start tests or implementation until the M2/M3 external approval gates pass and the route is regenerated on accepted M3.
- Do not read existing `.env`, credentials, private keys, Trust CI secrets, or production dumps.
- Do not run against a non-disposable database without the named migration/production approval.
