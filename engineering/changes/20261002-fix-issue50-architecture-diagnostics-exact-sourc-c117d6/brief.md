# Fix issue50 architecture diagnostics: exact source locations, malformed path and line-skip rejection, bounded architecture input preflight in verifier.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20261002-fix-issue50-architecture-diagnostics-exact-sourc-c117d6`
Created: 2026-10-02T22:27:58+00:00
Risk: medium
Complexity: standard
Domains: api

## Problem

Fix issue50 architecture diagnostics: exact source locations, malformed path and line-skip rejection, bounded architecture input preflight in verifier.

## Outcome

One bounded architecture input diagnostic identifies the blocking source before architecture binding, fitness and root discovery produce cascaded errors. Legal Unicode line lookalikes inside JSON strings do not change physical source coordinates.

## Scope

### In scope

- Architecture model/path diagnostics, doctor disclosure and the verifier's early architecture-inputs gate; focused regression coverage and this contour-local package.

### Out of scope

- A's verifier finalization and runner lifecycle, E's Git helpers, factory subset-contract preflight already on main, version/state/release identity, preserved dirty trees and deployed settings.

## Constraints

- Backward compatibility: valid models, canonical bytes, digests and generated views retain their existing contracts. Error metadata is additive.
- Data/privacy: local source-only reads use existing descriptor-relative no-follow primitives; no credentials or external service calls.
- Performance: existing byte, nesting, parsed-node and model bounds apply before consumers. D's focused processes use CPUs 8 and 9 with a two-process total.
- Operational: owner approved recovery design section D; controller owns full verification, selected reviews and PR-only delivery. Initial base e5856acfd4bc7a186f40a740b54ec86459462db5; actual main 63799f8760d3a55028d83ab5ff0116ececf8f7d1 was merged without conflicts into the isolated branch at ab24e1fbabbcadb893522edf946a0f01a1fa277f. Upstream artifact/state truth is preserved; this contour adds no version/state or publication change against that actual main.
