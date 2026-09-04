# Release plan — M6 bounded semantic validation on exact M5 85cd434

## Deployment

No deployment is authorized. This phase produces a repository-local provisional M6 source checkpoint only.

## Feature flags / staged rollout

Semantic composition remains disabled unless all coordinator, validator, adjudicator, store, and repair-broker dependencies are explicitly injected and ready. No live provider or application-write capability is shipped.

## Metrics and alerts

Future activation must monitor fixed semantic publication, evidence, verdict, repair, escalation, and recovery counters without task or actor labels. Any lineage, capability, replay, or append-only invariant failure is a stop condition.

## Go/no-go criteria

Local source go requires the seven finite criteria and focused evidence on one clean tree. PR, merge, release, deployment, provider use, persistent migration, and production go remain separate externally authorized gates.
