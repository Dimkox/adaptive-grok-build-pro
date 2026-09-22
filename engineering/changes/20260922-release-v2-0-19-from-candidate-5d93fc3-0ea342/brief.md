# Release v2.0.19 from candidate 5d93fc3

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260922-release-v2-0-19-from-candidate-5d93fc3-0ea342`
Created: 2026-09-22T23:29:46+00:00
Risk: high
Complexity: high-risk
Domains: security, api

## Problem

The repository is at published `v2.0.18`, while the verified post-release source work is a separate exact candidate tree. A new release must preserve the immutable `v2.0.18` record while carrying the candidate identity, its provenance and a reproducible package through the protected delivery chain.

## Outcome

`v2.0.19` is published from the exact artifact-child merge commit with a reproducible ZIP and SHA-256 sidecar. The release record is truthful about source, checks and publication, and does not imply deployment or autonomy activation.

## Scope

### In scope

- Candidate identity and lockstep release documentation.
- `PROJECT_STATE.json` release-chain provenance for the post-`v2.0.18` source.
- Local verification, route-selected independent reviews and fingerprint-bound receipts.
- Protected PR delivery, deterministic package build, exact tag and GitHub Release publication.

### Out of scope

- Provider installation, host mutation, production deployment or operational activation.
- Changes to deployed Trust CI policy, holdout, keys, branch protection or human trust stores.

## Constraints

- Backward compatibility: keep all published release bytes and historical facts unchanged.
- Data/privacy: never read or include credentials, private keys, `.env` files or host runtime state.
- Performance: package generation is bounded and deterministic; verification runs once on the final tree.
- Operational: merge, tag and release require exact-SHA external checks and named grants; no GitHub Actions or deployment.
