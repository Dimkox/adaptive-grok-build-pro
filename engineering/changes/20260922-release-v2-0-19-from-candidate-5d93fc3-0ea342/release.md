# Release plan — Release v2.0.19 from candidate 5d93fc3

## Deployment

Repository publication only: protected PR merge, exact tag `v2.0.19`, and GitHub Release assets. No service deployment, host mutation, provider activation or operational promotion.

## Feature flags / staged rollout

None. Product defaults and runtime activation flags remain unchanged and default-off.

## Metrics and alerts

Check exact-head Trust CI conclusion, artifact/sidecar digests, tag target and release asset names. Treat any mismatch as a no-go.

## Go/no-go criteria

GO only when local verification and all route-selected reviews pass on current fingerprints, the App-owned `adaptive-trust-ci/verified@06ecf1c875bc` check succeeds on the exact PR head, required signed Trust CI scopes are present, and the named local grants cover the exact branch/tag/release actions. Otherwise retain `v2.0.18` and stop.
