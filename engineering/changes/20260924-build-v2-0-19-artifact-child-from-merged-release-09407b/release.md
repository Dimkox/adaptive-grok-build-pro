# Release plan — Build v2.0.19 artifact child from merged release-sync 3f41be92

## Deployment

None. This change delivers repository bytes only; provider installation, host mutation and production deployment are forbidden.

## Feature flags / staged rollout

None. The release remains unpublished until the separate exact tag and GitHub Release actions.

## Metrics and alerts

Record deterministic build equality, source-parent/tree identity, ZIP digest, sidecar digest, exact PR head, Trust CI policy-epoch check and later tag target.

## Go/no-go criteria

- No-go on stale or mismatched source/head/tree, non-reproducible bytes, missing sidecar, secret/deployment findings, stale local evidence or failed external Trust CI.
- Go for artifact-child merge only after local verification, security/release reviews and external exact-head Trust CI PASS.
- Tag/release remain separate downstream go/no-go decisions requiring fresh exact grants and checks.
