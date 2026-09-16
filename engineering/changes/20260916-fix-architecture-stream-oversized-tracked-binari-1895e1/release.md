# Release plan — stream oversized tracked binaries

Repository change only; no deployment, no migration, no service impact. The architecture analyzer is used by `grok_verify` and by the external `repository-verification` command, so both paths are exercised by the pull request's own gate.

## Feature flags / staged rollout
None: behaviour is identical for every file at or below the existing limit, which is the whole installed population except tracked release artifacts.

## Metrics and alerts
- The architecture stage must report `drift/fitness/diagrams` without a `limit` error on a tree containing the v2.0.17 ZIP.
- Exact-head `adaptive-trust-ci/verified@06ecf1c875bc` conclusion.

## Go/no-go
Go when the fitness suite is green, `grok_verify --mode pr` passes and code/test reviews pass. No-go if any memory limit had to be widened to make the check pass — that would be the failure mode this change exists to avoid.
