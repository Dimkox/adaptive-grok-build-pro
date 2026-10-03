# Rollback plan — durable activation probe observations

## Trigger conditions

Stop rollout if v3 migration or startup recovery fails, operator authentication is not enforced, the API contract diverges from the served routes, retries can dispatch twice, provider failures expose raw content, or restored snapshots lose probe history. An ambiguous provider outcome is an expected durable state, not by itself a reason to replay or delete a record.

## Application rollback

Disable access to the probe routes through the normal service/configuration rollback boundary and keep the writer stopped while selecting a prior binary. A prior binary may open the database only if it explicitly supports schema v3 and preserves unknown probe rows. Never point a v1/v2-only binary at a v3 database. If no compatible reader is available, retain the service stopped and use a v3-capable build or forward fix.

## Data recovery / forward-fix

Do not delete probe rows, rewrite event history, or downgrade `user_version`. Preserve the current database and verified snapshot. If the application needs correction, ship an additive forward migration and retain the append-only table. If restoration is necessary, stop the landing and publication writers, preserve current roots, restore the verified snapshot with live mode disabled, and verify the database before startup. Restoring pending rows causes startup to append `unknown`; it does not repeat provider work.

## Verification after rollback

Confirm the selected binary can open the exact schema without migration loss; verify retained landing jobs and probe events by ID; verify operator routes are disabled or correctly authenticated; and confirm startup/GET cause no provider call. Keep `live_enabled=false` during rollback verification. Record unresolved `unknown` probes as ambiguous and preserve the prior result. The historical 769/191 event remains attested only and is never reconstructed by a new call.
