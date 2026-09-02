# Release plan — M8 earned autonomy provisional M4 bridge

## Deployment

None. This is a pure source checkpoint with no push, merge, release, activation or deployment authority.

## Feature flags / staged rollout

Dependency order: factual restacked M7 producer contracts → remove temporary reader → durable accepted/current lookup plus real shadow evidence → M8 verification/reviews/PR/external Trust CI → future restacked M9. Hard deadline: **2026-09-08 00:00 UTC+3**; no gate is waived.

## Metrics and alerts

Future fixed low-cardinality recommendation outcome, demotion trigger and cohort gate counters only; no PII or tuple labels.

## Go/no-go criteria

This bounded source correction can be reviewed locally. Go for factual qualification or activation requires removal of the temporary reader, durable accepted/current M7 evidence and >=30 real human acceptances for one exact tuple. No-go includes synthetic evidence, caller boolean authority, `blocked_pending_durable_lookup`, L3/L4, external-effect code, missing audit/threshold gates, stale tuple reuse, or any completion/activation claim from this package.
