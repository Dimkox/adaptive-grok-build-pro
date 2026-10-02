# Publish unverified transport branch for the assembled 2.1.0 release candidate; no merge tag or release

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20261002-publish-unverified-transport-branch-for-the-asse-051f6c`
Created: 2026-10-02T13:09:34+00:00
Risk: high
Complexity: high-risk
Domains: api

## Problem

Publish unverified transport branch for the assembled 2.1.0 release candidate; no merge tag or release

## Outcome

Deliver the exact 2.1.0 source candidate through a pull request with current local verification and independent release/security evidence. Publication, merge, tagging and activation remain separate gated actions.

## Scope

### In scope

- Exact `release/2.1.0-rc` tree, U4 exclusion, U0-U3/U5-U7 source inventory, release truth, PR delivery, rollback and dirty-worktree preservation.

### Out of scope

- Merge, tag, GitHub Release, deployment, provider activation, paid calls, live qualification and destructive dirty-worktree cleanup.

## Constraints

- Backward compatibility: additive/default-off behavior; PR3d migrations 024/025 remain unchanged.
- Data/privacy: no live provider or production data flow.
- Performance: bounded deterministic/offline checks; full verifier uses measured host capacity.
- Operational: PR-only; exact-head external Trust CI remains mandatory before merge.
