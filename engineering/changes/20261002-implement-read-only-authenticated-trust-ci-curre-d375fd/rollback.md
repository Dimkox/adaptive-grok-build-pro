# Rollback plan — Implement read-only authenticated Trust CI current-authority snapshot endpoint and bounded store queries with current public approval validation and short validity bound.

## Trigger conditions

Unexpected 200 responses for stale/revoked evidence, output containing approval signatures or private fields, unbounded acquisition, or regressions in existing webhook/worker/health/metrics behavior.

## Application rollback

Revert this additive endpoint/service/store/OpenAPI change through an isolated branch and reviewed pull request. Existing read endpoints, enqueue, approval submission and worker publication retain their prior behavior. Any installed runtime rollback requires a separate exact operational delegation.

## Data recovery / forward-fix

No migration, backfill, write, or new table is introduced. Durable job, approval and attestation rows remain intact. Never edit deployed policy, holdout, public trust or production database state from this source-delivery task.

## Verification after rollback

Run the full PR verifier and Trust CI unit/integration checks against the revert tree. Confirm the authority route is removed and prior authenticated read, webhook, metrics, health and publication regressions remain green. External exact-head Trust CI and signed approval requirements still apply.
