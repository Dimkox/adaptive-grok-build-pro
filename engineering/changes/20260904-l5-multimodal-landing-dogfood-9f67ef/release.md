# Release plan — L5 multimodal landing dogfood

## Current deliverable

This change produces unpublished local product candidate `2.0.14` and a deterministic site-candidate ZIP/sidecar while preserving published `v2.0.13` and its product ZIP as immutable history. Ready checkpoint `R` (this bookkeeping commit) is the package source parent and contains no `2.0.14` product pair; artifact child `A` is exactly `R` plus `packages/adaptive-grok-build-pro-v2.0.14.zip` and `packages/adaptive-grok-build-pro-v2.0.14.zip.sha256`, built reproducibly in two private no-local clones. Their tracked presence and matching sidecar identify `A`; nothing in this flow publishes the candidate, calls an operational provider, or claims a live/indexed site.

## Local go criteria

- Typed spec, schemas, runtime inventory, and architecture are consistent and placeholder-free.
- Focused contract/intake/provider/renderer/coordinator/artifact/API/publisher/compatibility tests pass once.
- Existing showcase, migrations `001`-`018`, M0-M9 contracts, and published product artifacts are byte-identical.
- The composite source gate is complete: product head `5f47508f3c0d52b71a3c866969cc28b6476a9d99` passed every heavy/product verifier gate except the source-AST policy ceiling, and policy head `58c9caed5d2c8f9febba297430a0782438505d82` changes only that bounded policy, its mirrored fixture and rationale and passes exact route fitness.
- All four route-selected reviewers pass the exact reviewed product/policy source; child `A` still requires its artifact-bound final gate.
- Default provider and publisher remain unavailable with proven zero external calls.

## Operational no-go boundary

The user explicitly delegated later branch push, pull-request creation/merge, tag push and GitHub Release publication for `v2.0.14`; those operations remain unavailable at `R` and require action/resource-bound local grants materialized only against exact child `A`. External Trust CI on the exact PR head remains merge authority. No provider call, data transfer, credential use, landing-target mutation, hosting, DNS/TLS/WAF action, deployment, or production effect is authorized; production also requires a current-site snapshot and restorable predecessor, pinned operational provider, real evaluator/Trust CI and signed artifact evidence, factual M8/M9 operational readiness, exact hosting configuration and staged recovery proof.

## Future staged activation

A separately designed operational change would stage the immutable artifact under its digest, compare the captured live baseline, activate atomically, verify canonical HTTPS content and preserved indexed routes, and restore only the exact predecessor on failure. Indexing is a distinct asynchronous observation and is never inferred from deployment or automated origin visibility.

## Signals

Report input/spec/profile/attempt/candidate/evaluator/ZIP/sidecar digests, disposition, cleanup, and zero-effect count. Never log raw input, provider native output, hidden fixture content, secrets, or unsupported live/SEO claims.
