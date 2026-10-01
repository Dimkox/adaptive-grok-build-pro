# Release plan — Factory v1.5 fast working release

## Deployment

PR-only source candidate. Deployment, merge, tag, and publication remain separate human-owned operations.

## Unified RC composition

- Product version: `2.0.19` candidate; no tag or release is created by this branch.
- Reviewed core input: `3a82f61b1ff4912571b39bd0bdceadd105149a58`.
- Payload range: exclusive parent `aa53f300d506736e61b36f627f8f12172ce8fbce` through aggregate head `29342400e3025c97d1cdc873b2682328680c5a56`.
- The exact specifications are committed at repository root. U4/macOS is excluded by owner decision and Windows remains fail-closed.
- Migrations `023`, `024`, and `025` are preserved as the first installable v1.5 lineage; payload contours add no SQL migrations.
- Historical `v2.0.19` ZIP/sidecar bytes predate this union and are not release artifacts for it. A replacement artifact child is required after source acceptance.

## Feature flags / staged rollout

Native core is available only after contract verification; optional package adapters and prediction influence remain off. All result channels stay unavailable and the dispatcher stays dormant. Apple is excluded.

## Metrics and alerts

Context bytes/entries, decision reasons, phase timing, cost completeness, result rejection/redaction/unavailable counts, semantic verdicts, qualification state.

## Go/no-go criteria

Go only with green focused/full verification, independent code/test reviews, exact-head App-owned Trust CI, no authority escalation, and honest deferred/excluded statuses. Do not publish the preserved pre-union `v2.0.19` package bytes.
