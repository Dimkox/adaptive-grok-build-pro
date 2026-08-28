# Release plan — M3-M9 production delivery continuation

## Deployment

M3 is delivered only as a stacked branch and pull request. It performs no runtime deployment. M4–M9 each require a later branch from current protected main after the predecessor merges.

## Feature flags / staged rollout

Governance records seed empty/candidate-only. No active rule is fabricated. Later M9 delivery uses preview, staging, signed promotion request, canary, and halt/rollback gates.

## Metrics and alerts

M3 exposes deterministic validation status/findings/digests. M9 must add health, error, latency, security, business-threshold and rollback outcome metrics correlated to exact SHA and trust profile.

## Go/no-go criteria

Go for M3 PR only with final verifier and all four independent reviews green. Merge requires the App-owned policy-epoch exact-SHA check and required signed scopes. Production promotion remains human-owned.
