# Release plan — Factory v1.5 fast working release

## Deployment

PR-only source candidate. Deployment, merge, tag, and publication remain separate human-owned operations.

The aggregate integration branch at source head `35b90f29` is a preview, not a
budget-eligible delivery PR. Its remote feature ref equals that source head. Use the
20-contour projected linear DAG in `evidence/stacked-delivery-plan.json` to create
independently routed, exact-base dependency contours; remeasure every actual delta and
split further if needed. Projections are not measurements. Existing limits remain unchanged.
Integrated-preview risk is red with architecture/contract/data/security approval scopes.
These declarations are not approvals; future stacked routes derive their own scopes.

## Feature flags / staged rollout

Native core available after contract verification; optional package adapters and prediction influence remain off. Apple is excluded.

## Metrics and alerts

Context bytes/entries, decision reasons, phase timing, cost completeness, result rejection/redaction/unavailable counts, semantic verdicts, qualification state.

## Go/no-go criteria

The monolithic preview is NO-GO: functional checks and reviews pass, but aggregate
architecture `code_budget` and dependent governance fail. A future contour is GO only
with its own green verification, independent reviews, exact-head App-owned Trust CI,
no authority escalation, and honest deferred/excluded statuses.
