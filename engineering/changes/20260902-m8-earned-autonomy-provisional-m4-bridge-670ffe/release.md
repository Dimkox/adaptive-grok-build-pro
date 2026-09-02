# Release plan — M8 earned autonomy provisional M4 bridge

## Deployment

None. This commit is documentation/specification only and cannot be pushed, merged, released or deployed by this task.

## Feature flags / staged rollout

Dependency order: accepted M4 → restacked/accepted M5 → restacked/accepted M6 → factual restacked/accepted M7 with real shadow evidence → M8 implementation/verification/reviews/PR/external Trust CI → future M9. Hard deadline: **2026-09-08 00:00 UTC+3**; no gate is waived.

## Metrics and alerts

Future fixed low-cardinality recommendation outcome, demotion trigger and cohort gate counters only; no PII or tuple labels.

## Go/no-go criteria

Go for implementation requires factual accepted M7 restack and >=30 real eligible human acceptances for one exact tuple. No-go includes synthetic evidence, L3/L4, external-effect code, missing audit/threshold gates, stale tuple reuse, or any completion/activation claim from this package.
