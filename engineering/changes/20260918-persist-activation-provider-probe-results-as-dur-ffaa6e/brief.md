# Persist future activation provider probes as durable observations (#121)

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed requirements.

Change ID: `20260918-persist-activation-provider-probe-results-as-dur-ffaa6e`  
Route ID: `ffaa6e006773`  
Risk: yellow; API, data, security  
Historical boundary decision: future probes become durable; the old 769/191 response remains attested only.

## Problem and outcome

The current synthetic activation probe returns usage, profile and response digests but leaves no durable source row. New operator-triggered probes must be independently queryable after restart and recoverable through the landing SQLite backup. Probe observations remain distinct from end-to-end landing jobs.

## Scope

### In scope

- Landing-only operator Unix-socket API to trigger a server-executed synthetic probe and read it by ID.
- Pending reservation committed before dispatch, idempotent key, one provider attempt at most, immutable safe terminal/ambiguous record.
- Dedicated append-only SQLite table and additive schema v3 migration, preserving v1/v2 data.
- Closed OpenAPI contract and route/authorization parity tests.
- Snapshot/restore tests and operator/runtime documentation.

### Out of scope

- Reconstructing or backfilling the historical 769/191 provider response.
- Converting probes into landing jobs or using client-submitted results as evidence.
- Automatic replay after an ambiguous crash, additional providers, or changing runtime defaults.
- Any production provider call during local tests or verification.

## Constraints

- Backward compatibility: sequential v1→v2→v3 and v2→v3 migration; frozen landing-job v1 remains unchanged.
- Data/privacy: persist digests and bounded facts only; never keys, raw prompt, provider body, or unbounded exceptions.
- Operational: SQLiteLandingJobStore remains the sole writer; UDS filesystem ACL plus operator actor kind and dedicated `landing:probe` scope.
- Recovery: normal SQLite backup/restore includes probe rows; ambiguous post-dispatch records are never silently re-issued.
