# Data review — Trust CI PostgreSQL integration

Change: `20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`  
Route: `f771ecaf458d` · reviewer: `data_reviewer` (read-only) · write owner: none (parent implemented)  
Reviewed: 2026-08-23  
HEAD: `2865fdc632860534c8ffc61aa9981844a0685b5d` (`fix: enqueue draft PRs and prove live PostgreSQL Trust CI state`)  
Skills: `/adaptive-delivery` + `data-change` + `verification-evidence`

**PASS.** Schema, live harness, restart recovery, and production SQL are coherent. I would not block on data grounds.

This reviewer did not re-execute Docker or SQL. Evidence is the committed tree, surrounding store/migrator/backup code, ops tests, and the recorded 8/8 + restart-drill claim on this SHA. No `.env`, private keys, or production dumps were read. No push, merge, or deploy.

---

## Verdict against the requested checks

| # | Check | Result |
| --- | --- | --- |
| 1 | `compose.test.yaml` named volume `trust-ci-pgtest-data` | **PASS.** Data dir is that named volume. No `tmpfs:`. Isolated from production `trust-ci-postgres`. |
| 2 | `down --volumes` in trap | **PASS.** Both `postgres-integration.sh` and `postgres-restart-drill.sh` trap `down --volumes --remove-orphans` on `EXIT` and clean first. |
| 3 | Live 8/8 postgres integration tests | **PASS (recorded, not re-run).** Eight `skipUnless` methods cover the required claim/lease/heartbeat/dead/idempotency/nonce/attestation/migration cases. Compose command is `unittest discover -p test_postgres_integration.py`. Commit message and `tasks.md` record 8/8. |
| 4 | Restart drill: job ID survives `compose restart` | **PASS.** Seed migrates + enqueues a fixed SHA job and prints `job_id`. After `compose restart postgres-test` + healthy wait, verify `ping()`s, looks up the SHA, fails if the row is gone or `base_sha`/`policy_digest` changed, and prints the same `job_id`. Named volume is what makes that restart meaningful (`compose restart` discards tmpfs). |
| 5 | No destructive production SQL | **PASS.** Numbered migrations are `CREATE`/`GRANT`/`REVOKE` only. Restore `--clean` is gated on `--confirm-disposable`. Test `TRUNCATE` lives in Python against the disposable DB, not in `.sql`. |

Would I block? **No.**

---

## What was actually inspected

```text
.git/HEAD, .git/refs/heads/feat/trust-ci-control-plane → 2865fdc
.git/COMMIT_EDITMSG
.git/logs/HEAD (04348db → 2865fdc)

engineering/changes/20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec/
  {brief,requirements,architecture,tasks,test-plan,rollback,state,route}.md/json
  evidence/analysis-{data_architect,architect,repo_explorer}.md

trust-ci/sql/{001_schema,002_operational_indexes,003_database_roles}.sql
trust-ci/src/adaptive_trust_ci/resources/ (byte-twin of sql/)
trust-ci/src/adaptive_trust_ci/{migrations,store,backup,metrics}.py
trust-ci/postgres/init/001_roles.sh
trust-ci/{compose.test.yaml,compose.yaml}
trust-ci/scripts/{postgres-integration,postgres-restart-drill,restore-drill}.sh
trust-ci/tests/{test_postgres_integration,postgres_restart_probe,test_ops,test_database_roles}.py
trust-ci/env/{common,api,worker,migration,backup,postgres}.env.example
trust-ci/README.md
engineering/runbooks/trust-ci-rollout.md
decisions.md (named-volume restart)
.grok-stack/adaptive_grok/verification.py (_sql_safety)
```

---

## Schema before / after

Greenfield. No existing production catalog. After `adaptive-trust-ci migrate` the database has the checksum registry plus six application relations and the claim function.

### Registry (migrator, not a numbered file)

`trust_ci_schema_migrations(version PK > 0, name UNIQUE, sha256 char(64), applied_at)`. Advisory lock `0x41544349` (`ATCI`) serializes `status()` and `apply()`. Fail-closed on missing applied files, name drift, and checksum drift. No down migrations.

Packaged apply path is `adaptive_trust_ci.resources`. Ops twin is `trust-ci/sql/`. `test_packaged_migrations_match_deployment_migrations` requires equal filenames and equal bytes. Current files: `001_schema`, `002_operational_indexes`, `003_database_roles`.

### `001_schema.sql` — operational truth

- `trust_ci_jobs`: UUID PK; exact SHA/policy hex checks; unique `idempotency_key`; finite status; `attempts`/`max_attempts` 1–20; lease owner + expiry; JSON result.
- Partial indexes: queue `(status, created_at)` for live rows; PR history; head SHA.
- `trust_ci_job_attempts`: PK `(job_id, attempt_no)`, FK cascade.
- `trust_ci_approvals`: unique nonce `length >= 16`; exact SHA/policy binding; `expires_at > issued_at`.
- `trust_ci_attestations`: unique `job_id`, status `passed|failed`, payload + signature.
- `trust_ci_events`: reserved audit table. No application writer.
- `trust_ci_claim_job`: dead-letter expired leases at attempt limit (`attempts-exhausted-after-worker-loss`), then `FOR UPDATE SKIP LOCKED LIMIT 1`, increment attempts, insert attempt row.

### `002_operational_indexes.sql`

Non-unique `IF NOT EXISTS` only: lease expiry, terminal finished, approval expiry, attempts-by-worker, attestation recency. No table rewrite. `CREATE INDEX` (not `CONCURRENTLY`) is acceptable on an empty P0 database; do not add `CONCURRENTLY` inside the transactional migrator.

### `003_database_roles.sql` + `postgres/init/001_roles.sh`

Privilege split, not a data rewrite. Init (first boot only) creates non-superuser `trust_ci_api` / `trust_ci_worker` / `trust_ci_migrator` / `trust_ci_backup`, revokes `CREATE`/`CONNECT` from `PUBLIC`, and grants schema `CREATE` only to the migrator.

`003` then:

- revokes table/sequence/function rights from `PUBLIC`;
- API: `INSERT` jobs and approvals; **no** attestation insert; **no** `EXECUTE` on `trust_ci_claim_job`;
- worker: `UPDATE` jobs, attempt insert/update, attestation insert, `EXECUTE` claim;
- backup: `SELECT` only.

Test compose now mounts the same init scripts and uses migrator as `TRUST_CI_TEST_DATABASE_URL`, with extra API/worker/backup DSNs exported. Production `compose.yaml` already mounted `./postgres/init` and uses a durable `trust-ci-postgres` volume.

---

## Query plan and index impact

Expected volume is small: one durable job per `(repository, PR, head SHA, policy digest)`, `max_attempts` default 3 (cap 20), one attestation per finished job. No partitioning or retention job.

Claim shape uses `trust_ci_jobs_queue_idx` plus `trust_ci_jobs_lease_expiry_idx`. The `OR` (queued vs expired lease) is not a single perfect index; at this volume that is fine. `SKIP LOCKED` avoids lock convoy.

Hot paths:

| lookup | support |
| --- | --- |
| `get_job` | PK |
| `get_job_for_sha` | `trust_ci_jobs_head_idx` |
| `has_valid_approval` | `trust_ci_approvals_lookup_idx` |
| `get_attestation` | unique `job_id` |
| enqueue conflict | unique `idempotency_key` |
| nonce replay | unique nonce |
| expired-lease metric | `trust_ci_jobs_lease_expiry_idx` |

All application `UPDATE`s have `WHERE` (job id + owner + live lease, or repo/PR/status). Metrics snapshot is five aggregate counts and `ROLLBACK`s so it never writes.

---

## Live 8/8 harness

`PostgresIntegrationTests` is skipped unless `TRUST_CI_TEST_DATABASE_URL` is set. `setUpClass` applies checksum-locked migrations. `setUp` truncates application tables and keeps the registry.

| # | Method | Handoff scenario |
| --- | --- | --- |
| 1 | `test_migration_registry_is_current_and_idempotent` | migrate idempotent; pending empty |
| 2 | `test_two_concurrent_workers_cannot_claim_same_live_job` | two workers, one winner, `attempts=1` |
| 3 | `test_expired_database_lease_is_reclaimed_by_another_worker` | reclaim + `attempts=2` |
| 4 | `test_heartbeat_requires_current_lease_owner` | non-owner heartbeat denied |
| 5 | `test_expired_lease_at_attempt_limit_becomes_dead` | `dead` / `attempts-exhausted-after-worker-loss` |
| 6 | `test_duplicate_webhook_identity_returns_same_job` | idempotent enqueue |
| 7 | `test_approval_nonce_replay_is_rejected_by_database_constraint` | unique nonce → `ReplayError` |
| 8 | `test_signed_attestation_survives_new_store_instance` | reconnect + offline verify |

`postgres-integration.sh` uses a PID-scoped Compose project, `--exit-code-from postgres-integration`, and always destroys the named volume. `test_postgres_integration_runner_cleans_up_after_itself` locks the trap text.

Recorded result on this SHA (commit message + `tasks.md`): 8/8. Captured stdout is not stored under the change package. Independent re-run was not performed here.

---

## Recovery

### Why the named volume exists

`decisions.md`: `compose restart` stops the container and discards tmpfs. `trust-ci-pgtest-data` plus trap `down --volumes` proves catalog recovery without leaving data behind. `test_postgres_restart_drill_uses_named_volume_and_container_restart` forbids `tmpfs:` and requires the volume mapping plus `compose restart postgres-test`.

Test volume name does not collide with production `trust-ci-postgres`. Compose prefixes the test volume with the isolated project name (`adaptive-trust-ci-pgtest-…` / `adaptive-trust-ci-pgrestart-…`).

### Restart drill

```text
cleanup (down --volumes)
up -d --wait postgres-test
postgres_restart_probe seed   # migrate, enqueue PR 799, print job_id
compose restart postgres-test
up -d --wait postgres-test
postgres_restart_probe verify # ping, get_job_for_sha, identity check, print job_id
postgres restart drill: PASS
```

Verify fails closed if the job disappeared or `base_sha`/`policy_digest` changed. Init scripts do not re-run after restart (data dir is non-empty), so roles and rows must come from the volume. The shell does not capture seed `job_id` and `test` it against verify; equality is implied because verify does not enqueue. Residual only.

### Production rollback / restore

- Product commits revert; no force-push of `main`.
- No down-SQL. Forward recovery is restore from custom-format `pg_dump` + SHA-256 manifest (`backup-create` / `backup-verify` / `restore-drill.sh`).
- `restore_drill` refuses unless `--confirm-disposable`. `pg_restore --clean --if-exists` therefore cannot target primary without that flag.
- Service rollback is previous image+policy+holdout; that changes the policy epoch and invalidates old jobs/approvals.
- Kill switch does not mutate rows.

Backfill: none. No historical jobs. Stop condition is not applicable.

---

## Destructive SQL

`sql-safety` flags `DROP TABLE/DATABASE/SCHEMA`, `TRUNCATE TABLE`, unbounded `DELETE`/`UPDATE` in `.sql`/`.php`.

| location | destructive? |
| --- | --- |
| `001_schema.sql` | no — `CREATE TABLE/INDEX/FUNCTION`, bounded `UPDATE` inside claim |
| `002_operational_indexes.sql` | no — `CREATE INDEX IF NOT EXISTS` |
| `003_database_roles.sql` | no — `GRANT`/`REVOKE`/`ALTER DEFAULT PRIVILEGES` |
| `postgres/init/001_roles.sh` | no — idempotent `CREATE ROLE` / `ALTER ROLE` / connect/create grants |
| `test_postgres_integration.py` `TRUNCATE … CASCADE` | yes, **test-only**, disposable DB, not a `.sql` file so `sql-safety` does not see it |
| `restore_drill` `pg_restore --clean` | yes, **gated** on `--confirm-disposable` |

`PostgresStore.migrate(sql)` can still execute arbitrary SQL outside the checksum registry. CLI does not use it. Leave it unused.

---

## Residuals (do not block this slice)

1. Change package has no captured 8/8 or restart-drill stdout; the claim lives in the commit message and `tasks.md`.
2. Restart drill prints both `job_id`s but does not `test "$seed" = "$verify"`.
3. Live class still runs as migrator. Exported API/worker/backup DSNs are unused, so 003 privilege isolation is not proven live (API cannot claim / cannot insert attestations).
4. `trust_ci_events` remains unused.
5. No partial unique index for one live job per `(repository, pr_number)`; two new heads can both stay active under `READ COMMITTED`.
6. Heartbeat writes Python `now`; claim expiry uses SQL `now()`. Bound NTP on the CI host.
7. README and `engineering/runbooks/trust-ci-rollout.md` still say `--exit-code-from tests`. The working script correctly uses `postgres-integration`. Copy-paste of the stale line fails.
8. `test_migration_registry_is_current_and_idempotent` asserts `>= 2` applied rows, not exactly 3.
9. Production example DSNs still omit `sslmode`; require `sslmode=require` (or stricter) for any non-Compose PostgreSQL.
10. Pre-implementation analysis still describes tmpfs; the implementation and `decisions.md` superseded that.

---

## Recommendation

**Pass `data_review`.** PostgreSQL remains the operational source of truth. The disposable harness uses a named volume, always destroys it, has eight live integration tests, and a restart drill that fails if the seeded job identity is lost. Numbered migrations are non-destructive. Restore remains confirm-disposable.

This is not merge authority. Merge still requires the App-owned policy-epoch check on the exact PR SHA.
