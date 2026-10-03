# Release plan — durable activation probe observations

## Deployment

Deliver the SQLite v3 migration, landing-only API, closed OpenAPI contract, tests, and operator runbook together. Deploy only through the repository's normal reviewed release path. Keep the service's existing `live_enabled` setting unchanged; this feature does not enable provider execution by itself. Probe POST is available only when the dedicated landing host has an explicitly configured eligible provider profile and only to an operator actor with `landing:probe` on the Unix socket.

Before rollout, take a verified landing-state snapshot while the writers are stopped. Confirm that the deployed reader supports schema v3 before opening a database that has been migrated. Migration is forward-only: it preserves v1/v2 job records, creates an independent append-only probe event table, and does not recast probes as jobs. Existing API v1 remains frozen.

## Feature flags / staged rollout

There is no separate activation flag. Default-off runtime mode retains the read route and has no configured probe runner; POST fails closed as unavailable. With a selected, explicitly enabled Qwen runtime profile, an authorized operator may make one synthetic probe. The API is not exposed by the general Factory application. Do not provision new credentials or enable a live profile as part of source delivery.

The operator must use one stable idempotency key per intended probe and retain its `probe_id`. A committed pending record precedes provider dispatch. Same-key retries never dispatch again. Pending state recovered after a restart becomes `unknown` with `outcome_ambiguous`; only a deliberate new probe with a new key can initiate another possible provider charge.

## Metrics and alerts

Read the durable record by `probe_id` for state, profile/model identity, request attempt count, elapsed time, usage and allowlisted failure category/status. Treat `provider_attempts: 1` as the local dispatch intent, not proof of provider receipt or billing. Alert on repeated `unknown` results, migration errors, or unavailable configured profiles through existing operator monitoring; do not add high-cardinality probe identifiers to metrics.

## Go/no-go criteria

Proceed only when v1/v2 migration tests pass, v3 snapshot/restore retains probe event rows, route/auth parity tests pass, and the runbook's ambiguous recovery instructions are available to operators. Stop if schema identity is unexpected, the migration fails, or the exact reader cannot reopen the migrated state. Do not run a live probe as a release check without its separate operational authority. Trust CI and required human security approvals remain independent merge gates.
