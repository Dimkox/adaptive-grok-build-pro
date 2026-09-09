# Release plan — Consolidate milestone branch state and delivery

## Deployment

Source documentation only. Deliver through this isolated branch and a pull request to the then-current protected `main`; do not deploy Trust CI, mutate GitHub, merge, tag, or publish as part of implementation. Re-fetch and refresh the snapshot if `origin/main` or any inventoried PR head moves before the state PR is finalized.

## Feature flags / staged rollout

No feature flag. The PR is the atomic rollout unit for `PROJECT_STATE.json`, README, `START_HERE.md`, tests, `mistakes.md`, and this change package. Do not split the state model from its human handoff or regressions.

## Metrics and alerts

Pre-merge signals are JSON/spec parse success, exact epoch/App agreement, known milestone fact assertions, retained work inventory, exact K16/120 graph completeness, and an allow-listed clean diff. After merge, the observable is that a fresh clone reaches the consolidated delivery handoff without chat.

## Go/no-go criteria

Go only if focused checks and route-selected reviews pass on the final fingerprint, the PR is up to date with protected `main`, and the App-owned exact-head check is `adaptive-trust-ci/verified@06ecf1c875bc` from App `4694114` with any required signed scope. Any changed observation, stale review, missing unique-work entry, graph mutation, forbidden path, or external gate gap is no-go.
