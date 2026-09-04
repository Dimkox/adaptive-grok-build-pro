# Release plan — L5 multimodal landing dogfood

## Current deliverable

This change produces unpublished local product candidate `2.0.14` and a deterministic site-candidate ZIP/sidecar while preserving published `v2.0.13` and its product ZIP as immutable history. Source-freeze `F` contains no `2.0.14` product ZIP; that pair is built twice only from ready-state child `R` and added alone in artifact child `A`. Nothing in this flow publishes the candidate, calls an operational provider, or claims a live/indexed site.

## Local go criteria

- Typed spec, schemas, runtime inventory, and architecture are consistent and placeholder-free.
- Focused contract/intake/provider/renderer/coordinator/artifact/API/publisher/compatibility tests pass once.
- Existing showcase, migrations `001`-`018`, M0-M9 contracts, and published product artifacts are byte-identical.
- One exact-head PR verifier passes and the four route-selected reviewers record no critical/core/authority/tenant/data-loss blocker against the same fingerprint.
- Default provider and publisher remain unavailable with proven zero external calls.

## Operational no-go boundary

Push/PR/merge/release and any provider/data-transfer/hosting action require new exact authorization. Production additionally requires a current-site snapshot and restorable predecessor, pinned operational provider, real evaluator/Trust CI and signed artifact evidence, factual M8/M9 operational readiness, exact hosting/TLS configuration, staged recovery proof, and action/resource-bound grants. Until every item exists, the only release target is local source/artifact readiness.

## Future staged activation

A separately designed operational change would stage the immutable artifact under its digest, compare the captured live baseline, activate atomically, verify canonical HTTPS content and preserved indexed routes, and restore only the exact predecessor on failure. Indexing is a distinct asynchronous observation and is never inferred from deployment or automated origin visibility.

## Signals

Report input/spec/profile/attempt/candidate/evaluator/ZIP/sidecar digests, disposition, cleanup, and zero-effect count. Never log raw input, provider native output, hidden fixture content, secrets, or unsupported live/SEO claims.
