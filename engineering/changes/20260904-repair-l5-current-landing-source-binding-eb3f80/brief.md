# Repair L5 current landing source binding

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260904-repair-l5-current-landing-source-binding-eb3f80`
Created: 2026-09-04T18:29:22+00:00
Risk: medium
Complexity: standard
Domains: ai, api

## Problem

Repair the delivered L5 exact runtime source binding and deterministic artifact inventory for the current landing repository. Update the pinned source revision and protected style asset handling, keep generator write scope unchanged, preserve the published non-deployed OpenAPI snapshot, and add regression coverage. Preserve previously published artifacts and perform no provider calls or target mutation.

## Outcome

The offline L5 pipeline accepts the current landing repository identity
`699010380f4f90a0193a9c22090c35e6aded7d2c` / tree
`f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4`, preserves its extracted
`index.css`, and seals a complete 20-member site artifact. The generator still
writes only `index.html` and `content.css` and gains no provider, publisher, or
production authority.

## Scope

### In scope

- Atomically update the renderer/service exact source SHA/tree while retaining
  the byte-identical published OpenAPI `1.0.0` snapshot as non-deployed history.
- Accept the exact protected `/index.css` source link and reject inline,
  duplicate, remote, or unknown stylesheet surfaces.
- Add `index.css` to the closed deploy inventory with source provenance while
  keeping `LANDING_WRITE_PATHS` unchanged.
- Add regression-first focused coverage, current handoff documentation, and
  exact-tree verification/review evidence.

### Out of scope

- Provider execution, durable job runtime, cPanel/LiteSpeed publication, live
  deployment, DNS, indexing, credentials, secrets, or target mutation.
- Rewriting historical L5 design/evidence or rebuilding published `v2.0.14`.
- Designing or publishing the separately versioned config-neutral successor API.
- General HTML/CSS sanitization, arbitrary source revisions, frameworks, or a
  second generator write path.

## Constraints

- Backward compatibility: v1 record schemas and runtime operations stay
  unchanged; the old or mixed exact-source tuple intentionally fails with
  HTTP 409. The frozen OpenAPI snapshot is not runtime configuration authority.
- Data/privacy: source bytes remain local exact-Git inputs and are never sent
  to a provider by this repair.
- Performance: no dependency or runtime phase is added.
- Operational: one focused red-green cycle, one full verifier, one review
  wave; no package rebuild or external effect.
