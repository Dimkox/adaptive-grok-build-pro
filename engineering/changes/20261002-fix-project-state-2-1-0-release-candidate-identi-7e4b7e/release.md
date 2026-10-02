# Release plan — Fix PROJECT_STATE 2.1.0 release candidate identity so the new source-only candidate has no artifact hashes while preserving the immutable 2.0.19 artifact record

## Deployment

No deployment. This correction ships only through the candidate PR.

## Feature flags / staged rollout

Not applicable.

## Metrics and alerts

State/manifest binding test status and exact candidate SHA.

## Go/no-go criteria

GO for PR review when lockstep tests pass. NO-GO if candidate fields claim an artifact or delivery event.
