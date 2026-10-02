# Release plan — Publish unverified transport branch for the assembled 2.1.0 release candidate; no merge tag or release

## Deployment

No deployment in this package. Push the isolated branch, open a PR, require local receipts and the App-owned exact-head Trust CI check. Merge/tag/GitHub Release require separately delegated actions.

## Feature flags / staged rollout

All new provider-facing and optional U5/U6 behavior stays dormant, observation-only, deterministic offline or explicitly unqualified. Activation is a successor decision.

## Metrics and alerts

Track exact PR head SHA, local verification fingerprint, Trust CI check name/app/status, migration/restart results, and any surviving review mutant.

## Go/no-go criteria

GO for PR review only after full local verifier and independent security/release reviews pass on the same tree. NO-GO for merge while Trust CI or required approvals are missing; NO-GO for tag/release until the exact merged commit and reproducible artifact exist.
