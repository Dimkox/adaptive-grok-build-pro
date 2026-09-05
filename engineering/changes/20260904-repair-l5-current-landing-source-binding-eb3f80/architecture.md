# Architecture — Repair L5 current landing source binding

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

The L5 runtime pin and the published non-deployed OpenAPI snapshot name landing
`176efca...` / tree `f2bdce...`. The current clean landing revision extracted its only inline
style to protected `/index.css`. Current code first rejects the new identity,
then rejects the no-inline-style source; a parser-only repair would still seal
an incomplete 19-member artifact without `index.css`.

## Proposed behavior

Rotate the accepted source epoch atomically to
`699010380f4f90a0193a9c22090c35e6aded7d2c` / tree
`f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4`. Bind the exact `/index.css`
source tag as protected surface, allow only the renderer-owned `/content.css`
addition, and add `index.css` as the 20th deploy member with source provenance.

## Components and boundaries

- `landing_renderer.py`: exact source identity, closed surface validation, and
  unchanged two-path write boundary.
- `landing_artifact.py`: closed 20-member deployment allowlist and manifest.
- `landing-dogfood.v1.json`: byte-identical published `1.0.0` non-deployed
  snapshot; it is not current runtime-configuration authority.
- Provider/publisher, database, Trust CI, packages, target repository, and live
  site are outside this repair and remain unchanged.

## Data flow

Exact read-only landing tree → validate protected source surface → replace
escaped `<main>` plus append generated `content.css` → verify two-path Git
delta → seal sorted 20-member artifact. `index.css` flows only from the exact
source tree to source-provenance archive member.

## API and event contracts

Four `/v1` runtime operations and all six v1 record schemas remain unchanged.
New submissions must carry the renderer/service exact SHA/tree; the old or a
mixed tuple keeps the existing HTTP 409 `source_identity` behavior. The rich
landing OpenAPI remains byte-identical at published version `1.0.0` because it
is not dynamically served or used as runtime configuration. A separately
scoped, config-neutral successor contract is required before this endpoint is
represented as a current deployable public API; no event contract changes.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: existing L5 exact-source, bounded-write, deterministic
  artifact, and external-authority rules.
- Applicable canonical example IDs/versions: no new example.
- Open debt: a config-neutral, separately versioned landing API contract is
  deferred; this repair does not claim a deployed/public API cutover.
- Expected governance handoff or receipt impact: fresh route-bound verifier
  plus `code_review`, `test_review`, and `security_review` receipts.

## Bitrix-specific impact

- Modules/events/agents/components affected: none; Bitrix is not in scope.
- Cache and managed cache impact: none.
- Installation/update/uninstall impact: none.
- Core modification: forbidden unless explicitly approved.

## Decisions

- Historical `v2.0.14` remains a truthful 19-member release; this branch is an
  unreleased forward repair and does not rewrite old evidence.
- `index.css` is trusted only through exact repository/SHA/tree identity and
  remains outside `LANDING_WRITE_PATHS`.
- The frozen OpenAPI remains an immutable historical repository snapshot;
  current source authority lives in renderer/service configuration until a
  separately scoped config-neutral successor exists.
- No generalized source selector or sanitizer is introduced.

## Risks and mitigations

- A stale OpenAPI could be mistaken for runtime authority: characterize its
  exact published bytes and explicitly exclude it from current API claims.
- Accepting external CSS could widen active content: allow only the exact
  `/index.css` source tag and preserve its Git object/mode.
- Artifact could render unstyled: assert referenced root stylesheets are in
  the ZIP and member count is exactly 20.
