# #121 storage, migration and backup analysis

Base inspected: `2f66ba6ef82d0f6a0bb3a4389e7f03b393c99217`; product code left unchanged.

## Current durable boundary

`factory/src/adaptive_factory/landing_server.py::build_landing_app` composes one `SQLiteLandingJobStore` for the dedicated Unix-socket host and closes it with the app lifespan. Provider calls happen through the API-owned `LandingApplicationService`; the separate `landing_live_executors.py::probe_qwen` CLI directly invokes the HTTP normalizer and returns sanitized JSON to stdout, bypassing both API and store.

The store is intentionally closed-schema (`landing_sqlite_store.py`): `SCHEMA_VERSION = 2`; version 1 upgrades by adding nullable `observation_json` to `landing_jobs`; `_validate_schema` compares the complete `sqlite_schema` table inventory against exactly `landing_commands` and `landing_jobs`, then checks every column, STRICT/table metadata and FK layout. An extra table or column currently fails closed. Job observations are attached to mutable `landing_jobs` rows and `_validate_record` binds observation input/profile evidence back to the job. Consequently, manufacturing a probe as a synthetic `LandingJobRecord` would conflate it with normal accepted/normalized/rendered/published job state and its recovery/API lifecycle.

## Migration impact if probes become durable

Prefer a separate append-only probe record/table with its own `probe_id`, idempotency/digest rule and closed record decoder. It can reuse the existing sanitized provider observation/evidence facts (profile/input/request/response digests, state/category, usage, elapsed/timestamps), but should not require a `LandingInputV1`, artifact, tenant/repository job identity, nor enter `_recover_interrupted`/landing state transitions. Persist only allowlisted facts and digests; no API key, request Authorization/header, raw provider body, or model output. The standalone probe should report a distinct `probe_id`; historical `job_id` text must remain an explicitly sourced historical value, not a fabricated `landing_jobs` primary key.

A new table requires coordinated updates in `landing_sqlite_store.py`: bump schema version to 3; add a v2→v3 transactional migration and retain a valid sequential v1→v2→v3 path; update exact `_schema_inventory` and column/FK/STRICT validation; include ownership/idempotent append checks. Existing schema-drift tests in `factory/tests/test_landing_sqlite_store.py` should continue to reject unrecognized tables/columns. Add migration tests for empty install, valid v1 and v2 upgrades with existing jobs/observations unchanged, restart/reopen durability, duplicate `probe_id` identical replay versus conflicting digest, and tamper/unknown-field rejection.

There is a distinct PostgreSQL migration chain (`factory/src/adaptive_factory/resources/001...018.sql`) for the core factory control plane; it is not this host's landing store. Do not put local landing probe records into those PostgreSQL migrations.

## Backup/restore implications

`factory/src/adaptive_factory/landing_backup.py` snapshots the entire landing SQLite DB through SQLite's online backup API under the same writer lock, so an additional table in that DB is included automatically and no second snapshot root/artifact class is needed. Snapshot records `provider_replay: false`; restore insists on that flag and requires provider execution disabled, returning `restored_inactive`. This is the correct boundary: restoring evidence must never replay a provider request.

Schema acceptance is version-sensitive in `_snapshot`: it currently accepts only `(APPLICATION_ID, SCHEMA_VERSION)` and historical `(APPLICATION_ID, 1)`. With v3, explicitly accept v2 snapshots as well as v1 while preserving their exact bytes/state; restore should not mutate the copied DB, and normal store startup should apply sequential migrations. Extend backup tests to snapshot/restore a populated probe row, verify its facts survive and provider_replay remains false, and prove backup imports remain offline (existing blocked-import list includes API/server/host/live executors).

Relevant tests: `factory/tests/test_landing_sqlite_store.py` exact inventory/schema drift, migration and reopen tests; `factory/tests/test_landing_backup.py::test_round_trip_restores_inactive_sqlite_and_artifacts_without_replay`, schema identity/snapshot test and offline import guard; `factory/tests/test_landing_server.py` owns writer lifecycle and store lock; `factory/tests/test_landing_live_executors.py` probes sanitized CLI output but currently patches the provider call and has no persistence assertion.
