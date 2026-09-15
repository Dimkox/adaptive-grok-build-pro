# Data change evidence

## Backend schema and compatibility

Landing SQLite advances from schema v1 to v2 by adding nullable `observation_json BLOB` to `landing_jobs`. Existing tenant/repository/job primary keys and command bindings remain intact. Historical rows retain null observations; there is no backfill that invents provider attempts or accounting. The migration is an expand step and runs under the existing exclusive writer/startup transaction.

The explicit version-2 migration remains in the SQLite store alongside its embedded schema/version logic. The generic `resources/*.sql` history belongs to the separate PostgreSQL control plane; assigning SQLite its next PostgreSQL sequence number would conflate two databases. This representation preserves the existing migration-policy thresholds and requires the same SQLite migration/backup/restart regression evidence.

Existing production row counts and distribution were not inspected. The change does not add an index or rewrite application data into a new table. Disposable schema analysis on SQLite 3.45.1 confirms exact tenant/repository/job lookup still uses the existing primary-key index; see `evidence/query-plans.json`. Production duration and large-volume throughput have not been measured.

## New caller journal

The separate private journal stores one request record, nullable input payload and expiry per logical job. Point lookup uses its job primary-key index. Expiry cleanup scans the bounded journal; the implemented ceilings are 10,000 retained job records and 64 MiB of retained input. Reaching capacity stops new admission rather than evicting deduplication history or silently recreating old requests.

SQLite uses a process ownership lock, full synchronous transactions and a private WAL. Input purge uses secure-delete/checkpoint support; records retain reconciliation metadata. Provider keys do not belong in the journal. Actor/configuration/source binding prevents another configuration from replaying or relabelling existing work.

## Rollout, validation and stop conditions

Drain and stop each old writer, preserve its exact configuration/source identity, and create its snapshot with the matching old binary before starting the new version. Keep provider execution disabled during migration/readiness qualification. The implementation checks application/schema identity, expected columns, foreign keys and SQLite integrity; unsupported/corrupt state or unavailable ownership stops startup. No handwritten production SQL is authorized by this document.

Regression evidence covers atomic observation persistence, v1 migration without fabricated history, interrupted requests, private-path failures and recovery. The full verifier and independent review remain required before delivery. Verify source/profile capability, observation availability and preserved historical rows after installation; provider inference qualification is a separate signal.

## Recovery

Prefer the compatible new reader with new submissions disabled while reconciling outstanding intents. Old binaries cannot read the upgraded store. Any binary downgrade requires stopped writers and a complete pre-upgrade snapshot while separately preserving post-upgrade jobs/artifacts for reconciliation; do not drop the new column or erase the journal to make a downgrade appear successful. Full operational resources and backup commands are in `evidence/operations-plan.md`.
