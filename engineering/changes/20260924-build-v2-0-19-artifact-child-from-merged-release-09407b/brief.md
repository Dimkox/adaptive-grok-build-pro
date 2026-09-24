# Build v2.0.19 artifact child from merged release-sync 3f41be92

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260924-build-v2-0-19-artifact-child-from-merged-release-09407b`
Created: 2026-09-24T19:56:40+00:00
Risk: high
Complexity: high-risk
Domains: security, api

## Problem

The release-sync PR has merged at exact commit `3f41be92161fef451a2dfa7451eb458ce8f022b3`, but the v2.0.19 ZIP and sidecar must be delivered as a separate artifact-only child. The artifact must be reproducible from that merged tree and must not be confused with the later tag and GitHub Release boundaries.

## Outcome

The repository contains the v2.0.19 ZIP and SHA-256 sidecar built twice byte-identically from the merged release-sync tree, and the candidate state names both digests and their source parent while keeping publication and operational activation false.

## Scope

### In scope

- `packages/adaptive-grok-build-pro-v2.0.19.zip` and its `.sha256` sidecar.
- Candidate-state, release documentation and coupled test updates proving source-parent and digest binding.
- Local verification, security/release reviews, exact PR delivery and the external exact-head Trust CI boundary.

### Out of scope

- Tagging, GitHub Release publication, provider installation, host mutation, deployment and operational activation.
- Changes to deployed Trust CI policy, holdout, keys, branch protection or human trust stores.

## Constraints

- Backward compatibility: preserve v2.0.18 and all prior immutable bytes and facts.
- Data/privacy: package tracked source only; never read or include credentials, private keys, `.env` or host runtime state.
- Performance: build twice from one exact source parent and compare bytes/digests.
- Operational: merge, tag and release remain exact-SHA protected actions with named grants; no deployment is implied.
