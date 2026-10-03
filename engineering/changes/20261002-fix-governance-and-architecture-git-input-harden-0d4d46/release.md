# Release plan — Fix governance and architecture Git input hardening: explicit repository object binding, controlled Git environment, filter-free committed reads and pinned bounded regular-file projections.

## Deployment

Source-only contour E for later v2.1.1 aggregation. No current version, state, tag, release, deployed policy, holdout or production change.

## Feature flags / staged rollout

Local helpers default to bounded refusal. Controller delivers an isolated PR after current full verification/reviews; merge/publication remain separately authorized external actions.

## Metrics and alerts

Existing JSON ok/code/error, exit status and verification/review reports make rejection observable. No new runtime service or alerting integration.

## Go/no-go criteria

GO requires all typed criteria, exact final full PR/review evidence, App-owned policy-epoch exact-head Trust CI and required external approvals. Focused results alone are not completion or merge authority.
