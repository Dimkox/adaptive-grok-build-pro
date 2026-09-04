# Rollback plan — L5 multimodal landing dogfood

## Trigger conditions

- Contract/digest ambiguity, cross-tenant exposure, raw-content retention, executable/path/network escape, provider fallback, fourth attempt, nondeterministic artifact, predecessor byte drift, or any reachable publisher transport.
- A focused verifier/reviewer finding classified as critical, authority/tenant/data-loss, or core-scenario failure.

## Repository-local rollback

1. Disable the L5 composition so intake returns the closed unavailable response.
2. Revert the coherent additive L5 commits in reverse order and remove only L5-owned content-addressed candidate artifacts. Existing showcase, M0-M9 source, migrations, published product ZIP, and release state are never reconstructed or modified.

Transient blobs and workspaces are destroyed on both success and failure; cleanup failure is recorded and quarantined for host cleanup, never reused. No database reversal exists because the scope adds no migration or persistent shared state.

## Forward recovery

A defect is repaired on a new exact source SHA. All affected candidate/evaluator/package evidence becomes stale and must be regenerated; it cannot be rebound. Missing provider, snapshot, Trust CI, signing, hosting, or production authority remains an unavailable state rather than a recovery bypass.

## Verification after rollback

Confirm L5 routes are unavailable, no fixed provider or publisher process ran, the generated domain path is absent from active source, all frozen showcase/migration/contract/package digests match the design base, and the pre-change focused structure/architecture checks pass.
