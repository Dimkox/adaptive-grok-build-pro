# Release

## Deployment

Source-only successor PR. No VERSION bump, no ZIP rebuild, no GitHub Release, no image rebuild in this slice. Published `v2.0.15` tag and ZIP stay immutable.

## Feature flags / staged rollout

None. Lazy imports take effect when the merged CLI is used. Existing deployed API/worker images are unchanged until a later operator rebuild.

## Metrics and alerts

None new. Operator docs keep: HTTP 2xx on `/approvals` is not merge authority.

## Go/no-go criteria

Go for opening the successor PR after local `grok_verify --mode pr` PASS and independent code/test reviews.

No-go for merge until App-owned `adaptive-trust-ci/verified@06ecf1c875bc` on the exact new head SHA plus required signed scopes.

No-go for claiming M8/M9/pilot/final-program completion.
