# Release plan — release-chain convention and inspected causes

This change performs no release action: no tag, no Release, no artifact and no installation. Delivery is a documentation pull request merged on the App-owned exact-head check only.

## Deployment

Merge to `main`; nothing to deploy or restart.

## Feature flags / staged rollout

Not applicable.

## Metrics and alerts

- `tests.test_project_state` green, since the changed values are asserted by exact-value pins.
- Exact-head `adaptive-trust-ci/verified@06ecf1c875bc` conclusion.

## Go/no-go

Go when the three causes match the retained job records and no published release record moved. No-go if any cause is inferred rather than quoted, or if this PR is used to slip a release action in.
