# Fix issue #73: rename current evidence fingerprint fields that trigger GitGuardian secret heuristics while preserving historical evidence immutability and schema/test compatibility.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260922-fix-issue-73-rename-current-evidence-fingerprint-147e64`
Created: 2026-09-22T19:14:44+00:00
Risk: high
Complexity: high-risk
Domains: security, api

## Problem

Fix issue #73: rename current evidence fingerprint fields that trigger GitGuardian secret heuristics while preserving historical evidence immutability and schema/test compatibility.

## Outcome

The flagged `authorization_tree_fingerprint` appears only in two immutable historical evidence
artifacts, so those bytes remain unchanged. The current delegated-grant producer now places the
tree binding under `grant_binding_digest`; the policy reader and landing publisher retain
compatibility with legacy `tree_fingerprint` grants and fail closed if both names are present.

## Scope

### In scope

- Confirm the historical-only location and preserve those artifacts unchanged.
- Rename the current local delegated-grant binding field to `grant_binding_digest`.
- Preserve read compatibility for schema-version-2 grants that use `tree_fingerprint`.
- Reject ambiguous grants containing both current and legacy names.
- Keep external GitGuardian disposition/allow-list work explicit and separate from local code.

### Out of scope

- Rewriting immutable `engineering/reviews/**` history.
- Renaming every `authorization*` or `*_digest` field globally.
- Generating or submitting any security approval/private key.

## Constraints

- Backward compatibility:
- Data/privacy:
- Performance:
- Operational:

## Gate

The user explicitly approved this bounded bugfix for the next release. The local gate artifact
records that decision as workflow evidence only; it is not a delegated operational grant or a
human-signed Trust CI approval.
