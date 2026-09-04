# Release plan — M5 bounded local execution control plane on exact M4 67dc4dd

## Deployment

This change produces a repository-local source checkpoint only. The present authorization does not permit provider invocation, migration application outside a disposable local database, service activation, push, pull request, merge, tag, release, deployment, external write, or production operation.

## Feature flags / staged rollout

`FACTORY_EXECUTION_ENABLED=false` remains the default. A future separately authorized activation may expose execution routes only after schema `001`-`017`, a trusted profile registry, snapshot broker, artifact broker, distinct artifact-attestor capability, and database readiness all pass before Unix-socket exposure.

## Metrics and alerts

Use fixed-cardinality counters for claim, terminal, recovery, cleanup, retry, denial, and quarantine outcomes. Logs and audit facts carry correlation and stable identifiers but exclude secrets, raw provider streams, prompts, environment values, and private reasoning.

## Go/no-go criteria

- Go for local source checkpoint: all nine typed criteria pass on one clean fingerprint with zero required local evidence gaps.
- No-go: M4 regression, incomplete trusted composition, authority/isolation bypass, data loss/corruption, partial terminalization, failed recovery, or stale evidence.
- External delivery/activation additionally requires exact PR-head Trust CI, required independent signed approvals, qualified host isolation, controlled credentials/egress, rollback readiness, and explicit named operational delegation.
