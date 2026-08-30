# Production-only human approvals

Change ID: `20260830-создать-и-реализовать-feature-нового-postgresql-75aa6d`
Created: 2026-08-30T09:48:27+00:00
Risk: high
Complexity: high-risk
Domains: data, api, event, security

## Problem

Interactive approval currently blocks protected PR changes long before production. Move human authority to a fail-closed, one-time production promotion without weakening automated merge authority.

## Outcome

Ordinary PRs complete App-owned exact-SHA Trust CI without interactive signatures. Production still requires a fresh human Ed25519 envelope bound to an independently proven merged commit, exact artifact, environment and active policy epoch.

## Scope

### In scope

- Separate frozen promotion and protected-branch provenance contracts.
- Mirrored additive PostgreSQL migration 004, append-only audit and atomic consume-once authority.
- `POST /promotions`, internal consumption boundary, offline CLI, metrics and runbooks.
- Local shadow/deny-only proof, externally operated automated-only policy cutover, autonomous PR delivery/merge, then exactly one human-signed production promotion at final deploy.

### Out of scope

- Production deployment or other external writes during implementation.
- Human private-key handling by agents or services.
- Auto-merge, GitHub Actions, destructive migration, or deletion of legacy approvals.
- Multi-repository/tenant expansion and arbitrary deployment-provider integration.

## Constraints

- Backward compatibility: keep `/approvals` and migrations 001–003 for rollback; add new versioned contracts only.
- Data/privacy: retain security evidence; never log secrets, signatures, bearer tokens or raw rejected payloads.
- Performance: indexed exact-tuple lookup, short transactions, bounded reconciliation and measured query plans.
- Operational: all dependencies fail closed; deployed policy and branch protection remain external human-owned controls.
