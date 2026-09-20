# Fix issue #158: the long-lived adaptive-trust-ci worker accumulates unreaped [git] defunct children (measured 4 over ~24h, NRestarts=0), so every subprocess path must reap on all outcomes including the accepted 'zombie_only' classification; locate the real leak empirically rather than assuming a missing wait, add a test whose control fails on current code, and keep exit-status classification and all attestation/policy semantics untouched.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260920-fix-issue-158-the-long-lived-adaptive-trust-ci-w-9f3462`
Created: 2026-09-20T01:18:49+00:00
Risk: medium
Complexity: standard
Domains: api

## Problem

Fix issue #158: the long-lived adaptive-trust-ci worker accumulates unreaped [git] defunct children (measured 4 over ~24h, NRestarts=0), so every subprocess path must reap on all outcomes including the accepted 'zombie_only' classification; locate the real leak empirically rather than assuming a missing wait, add a test whose control fails on current code, and keep exit-status classification and all attestation/policy semantics untouched.

## Outcome

Describe the observable user or business result.

## Scope

### In scope

- 

### Out of scope

- 

## Constraints

- Backward compatibility:
- Data/privacy:
- Performance:
- Operational:
