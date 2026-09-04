# Release plan — L5 multimodal landing dogfood

## Current deliverable

This change is published as repository product release `v2.0.14`. PR #24 checked exact head `66a7fe5c4a59b3ea7e1350b34e0a547faf5a9f57`, merged at `2026-09-04T16:56:37Z` as tag target `1751b5855e46782b9a1bfceb6e1ab0102cba03b0` with unchanged reviewed tree `618df086920c92179aa0e22a8c8d4ad30ebd9230`, and the GitHub Release was published at `2026-09-04T16:58:48Z`. The tag-bound ZIP SHA-256 is `b03c64e67ac757f7d84abfed407cbd0ace2771afd960c67e24684099b3cc0264`; `v2.0.13` remains immutable history, and neither release establishes a live/indexed site.

## Local go criteria

- Typed spec, schemas, runtime inventory, and architecture are consistent and placeholder-free.
- Focused contract/intake/provider/renderer/coordinator/artifact/API/publisher/compatibility tests pass once.
- Existing showcase, migrations `001`-`018`, M0-M9 contracts, and published product artifacts are byte-identical.
- The composite source gate is complete: product head `5f47508f3c0d52b71a3c866969cc28b6476a9d99` passed every heavy/product verifier gate except the source-AST policy ceiling, and policy head `58c9caed5d2c8f9febba297430a0782438505d82` changes only that bounded policy, its mirrored fixture and rationale and passes exact route fitness.
- All four route-selected reviewers passed, the final artifact-bound gate passed, and App-owned `adaptive-trust-ci/verified@06ecf1c875bc` passed checked head `66a7fe5c4a59b3ea7e1350b34e0a547faf5a9f57` as check run `101099224099` with attestation `9defb556-f703-4a13-b20a-8b88aa6781b4` / signer `0519cf1d47436f2e`; GitGuardian also reported `SUCCESS`.
- Default provider and publisher remain unavailable with proven zero external calls.

## Operational no-go boundary

The delegated GitHub repository operations were completed for exact checked artifact head `66a7fe5c4a59b3ea7e1350b34e0a547faf5a9f57` and immutable tag target `1751b5855e46782b9a1bfceb6e1ab0102cba03b0`. That authority is exhausted and did not include provider calls, data transfer, credential disclosure, landing-target mutation, hosting, DNS/TLS/WAF action, site deployment, indexing, or any production effect. Operational activation still requires a current-site snapshot and restorable predecessor, pinned operational provider, real evaluator/Trust CI and signed artifact evidence, factual M8/M9 readiness, exact hosting configuration, staged recovery proof, and new action/resource-bound authority.

## Future staged activation

A separately designed operational change would stage the immutable artifact under its digest, compare the captured live baseline, activate atomically, verify canonical HTTPS content and preserved indexed routes, and restore only the exact predecessor on failure. Indexing is a distinct asynchronous observation and is never inferred from deployment or automated origin visibility.

## Signals

Report input/spec/profile/attempt/candidate/evaluator/ZIP/sidecar digests, disposition, cleanup, and zero-effect count. Never log raw input, provider native output, hidden fixture content, secrets, or unsupported live/SEO claims.
