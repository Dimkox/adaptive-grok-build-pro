# Enforce and report route approval gates (#126)

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260917-enforce-and-report-route-approval-gates-126-e405d5`
Risk: high
Complexity: high-risk
Domains: security, api

## Problem

The router declares `human_gates`, but no authorization or status path consumes them. A production grant can therefore be used without satisfying a route-declared `production_action_approval` gate. A route field that appears mandatory but has no consumer creates a false control claim.

## Proposed outcome

Treat declared gates as local workflow/action controls, separate from delegated grants and external Trust CI approvals. Persist explicit human decisions in the active change package, bind them to the route, change, gate, and a digest of the approved scope, reject stale or missing decisions, and show each gate's state in `grok_status.py`.

## Scope

### In scope

- A typed, durable gate-decision artifact for explicit approve/decline decisions.
- Fail-closed gate validation before `approved` workflow transition and before a matching delegated production or external-write grant is materialized or consumed.
- Deterministic mapping from `scope_and_design_approval`, `production_action_approval`, and `migration_or_external_write_approval` to workflow/action boundaries.
- `grok_status.py` output with gate name, state, scope binding, and evidence path.
- Compatibility behavior where old routes have declared gates but no artifact: pending, never implicitly approved.
- Tests for missing, declined, stale, mismatched, and approved decisions and exact grant binding.

### Out of scope

- Trust CI service, deployed policy, holdout, signed-approval protocol, GitHub App, or branch-protection changes.
- Creating or submitting a human-signed Trust CI approval.
- Production writes, publishing, pushes, merges, or deployment.
- Treating a local gate decision or receipt as cryptographic identity, merge authority, or Trust CI approval.

## Constraints

- Existing exact delegated grants remain separately required; satisfying a gate never creates a grant.
- Gate decisions and local grants remain workflow evidence. External Trust CI remains the merge authority and verifies required signed scopes itself.
- Scope edits invalidate the decision; changing route/change identity or gate name also invalidates it.
- Missing or malformed evidence must block the relevant workflow/action and be visible as pending/invalid, not silently ignored.
