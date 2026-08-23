# Data architect analysis — Trust CI PostgreSQL schema, migrations, live scenarios

Change: `20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`
Route: `f771ecaf458d`
Agent: `data_architect` (read-only except this report)
Skill: `/adaptive-delivery` + `data-change`

PostgreSQL is the operational source of truth. Elasticsearch/OpenSearch and ClickHouse are not used. There is no backfill, no search projection, and no analytical warehouse in this contour.

## 1. Verdict

The packaged schema already encodes the handoff contract: idempotent jobs, `FOR UPDATE SKIP LOCKED` leases, attempt-bounded dead-lettering, unique approval nonces, unique attestations, and checksum-locked forward-only migrations.

Live proof is split:

| Required scenario (handoff §2) | Where it is implemented | Runs in `unittest discover` with `TRUST_CI_TEST_DATABASE_URL` |
| --- | --- | --- |
| two workers claiming concurrently | `test_two_concurrent_workers_cannot_claim_same_live_job` | yes |
| lease expiry and reclaim | `test_expired_database_lease_is_reclaimed_by_another_worker` | yes |
| heartbeat ownership | `test_heartbeat_requires_current_lease_owner` | yes |
| attempt exhaustion to dead | `test_expired_lease_at_attempt_limit_becomes_dead` | yes |
| approval nonce replay rejection | `test_approval_nonce_replay_is_rejected_by_database_constraint` | yes |
| attestation durability | `test_signed_attestation_survives_new_store_instance` | yes (reconnect, not GitHub-outage replay) |
| PostgreSQL restart/recovery | `postgres-restart-drill.sh` + `postgres_restart_probe.py` | **no** — separate Compose drill |

`postgres-integration.sh` executes only `tests.test_postgres_integration` (eight methods, class-skipped without `TRUST_CI_TEST_DATABASE_URL`). Restart/recovery is a second command. README and `engineering/runbooks/trust-ci-rollout.md` still say `--exit-code-from tests`; the Compose service is `postgres-integration`. That stale name will fail if copied.

Image digest pins are required by Compose interpolation but are still `REPLACE_WITH_*_DIGEST` placeholders. The live PostgreSQL suite has not yet been executed in this change (handoff baseline: four skipped; current class has eight skippable tests).

Do not treat this report as production SQL authority. No production writes were performed.

## 2. Schema before / after

Greenfield. No existing production tables. After `adaptive-trust-ci migrate` the database contains the registry plus six application relations.

### 2.1 Registry (created by migrator, not a numbered file)

`trust_ci_schema_migrations`

| column | type | constraints |
| --- | --- | --- |
| version | integer | PK, `> 0` |
| name | text | UNIQUE, `^[a-z0-9_]+$` |
| sha256 | char(64) | `^[0-9a-f]{64}$` |
| applied_at | timestamptz | default `now()` |

Advisory lock id `0x41544349` (`ATCI`) serializes `status()` and `apply()`.

### 2.2 `001_schema.sql` — operational truth

Duplicated byte-for-byte in:

- `trust-ci/sql/001_schema.sql` (ops / `test_ops` text invariants)
- `trust-ci/src/adaptive_trust_ci/resources/001_schema.sql` (packaged apply path)

`test_packaged_migrations_match_deployment_migrations` fails if those trees drift.

**`trust_ci_jobs`**

- PK `job_id uuid`
- identity: `repository`, `pr_number > 0`, `base_sha`/`head_sha` char(40) lowercase hex, non-empty refs/pipeline
- `policy_digest` char(64) hex
- `idempotency_key` char(64) UNIQUE hex — SHA-256 of canonical JSON `{repository, pr_number, head_sha, pipeline, policy_digest}`
- finite `status`: `queued|leased|running|passed|failed|needs_approval|cancelled|dead`
- `attempts >= 0`, `max_attempts BETWEEN 1 AND 20`
- lease: `lease_owner text`, `lease_expires_at timestamptz`
- `failure_code`, `result jsonb` default `{}`
- timestamps: `created_at`, `updated_at`, `started_at`, `finished_at`

Partial indexes in 001:

- `trust_ci_jobs_queue_idx (status, created_at) WHERE status IN ('queued','leased','running')`
- `trust_ci_jobs_pr_idx (repository, pr_number, created_at DESC)`
- `trust_ci_jobs_head_idx (repository, head_sha, created_at DESC)`

**`trust_ci_job_attempts`**

- PK `(job_id, attempt_no)`, `attempt_no > 0`
- FK `job_id` → jobs `ON DELETE CASCADE`
- `worker_id` non-empty, `status` default `leased`, `error`, `result jsonb`

**`trust_ci_approvals`**

- PK `approval_id`
- `nonce text UNIQUE` with `length(nonce) >= 16`
- exact binding: repository, pr_number, base_sha, head_sha, policy_digest, scope, actor, key_id, reason
- `issued_at`, `expires_at` with `CHECK (expires_at > issued_at)`
- `payload jsonb` + `signature`
- lookup index `(repository, pr_number, base_sha, head_sha, policy_digest, scope, expires_at DESC)`

**`trust_ci_attestations`**

- PK `attestation_id`
- `job_id uuid UNIQUE` FK `ON DELETE CASCADE`
- `status IN ('passed','failed')`
- `payload jsonb` + `signature`

**`trust_ci_events`**

- `bigserial` PK, optional `job_id` FK `ON DELETE SET NULL`, `event_type`, `actor`, `details jsonb`
- **no writer exists in application code.** Design says “audit events”; schema is reserved only. Replayed approvals, dead-lettering, and claim races are not persisted here.

**`trust_ci_claim_job(p_worker_id, p_lease_seconds)`**

Single PL/pgSQL function, `RETURNS SETOF trust_ci_jobs`:

1. reject empty worker id / non-positive lease seconds
2. mark expired `leased|running` rows with `attempts >= max_attempts` as `dead` (`failure_code = 'attempts-exhausted-after-worker-loss'`)
3. pick one candidate `ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1` where `attempts < max_attempts` and (`queued` or expired `leased|running`)
4. set `leased`, increment `attempts`, assign owner, set `lease_expires_at = now() + make_interval(secs => p_lease_seconds)`
5. insert attempt row `ON CONFLICT DO NOTHING`

`PostgresStore.claim` ignores the Python `now=` argument (`del now`) and uses the database clock.

### 2.3 `002_operational_indexes.sql`

Non-unique, `IF NOT EXISTS`, no data rewrite:

| index | definition | intended query |
| --- | --- | --- |
| `trust_ci_jobs_lease_expiry_idx` | `(lease_expires_at) WHERE status IN ('leased','running')` | reclaim + expired-lease metric |
| `trust_ci_jobs_terminal_finished_idx` | `(status, finished_at DESC) WHERE status IN ('passed','failed','cancelled','dead')` | terminal listing |
| `trust_ci_approvals_expiry_idx` | `(expires_at) WHERE expires_at IS NOT NULL` | expiry scans; predicate is redundant (`expires_at` is NOT NULL) |
| `trust_ci_job_attempts_worker_idx` | `(worker_id, started_at DESC)` | worker attempt history |
| `trust_ci_attestations_created_idx` | `(created_at DESC)` | attestation recency |

No `UNIQUE` partial index on “one active job per PR”. Concurrent enqueue of two new heads can commit two live jobs (see §9).

## 3. Migration contract

Implemented in `trust-ci/src/adaptive_trust_ci/migrations.py`.

Discovery rules:

- filename `^(?P<version>[0-9]{3})_(?P<name>[a-z0-9_]+)\.sql$`
- versions contiguous from `001`
- unique version and unique name
- UTF-8 only
- SHA-256 of raw bytes stored in the registry

`plan_migrations` fail-closed on:

- applied version missing from package
- name drift
- checksum drift

`apply()`:

1. `pg_advisory_xact_lock(0x41544349)`
2. ensure registry
3. plan
4. execute each pending SQL file, then `INSERT` registry row
5. commit; rollback on any exception

There are **no down migrations**. Rollback is restore from custom-format `pg_dump` (`backup-create` / `restore-drill.sh`), then re-enqueue jobs as needed. Editing an already-applied file is forbidden; function changes must be a new numbered file because `CREATE OR REPLACE FUNCTION` in `001` will not re-run after the checksum is recorded.

CLI:

```text
adaptive-trust-ci migrate            # apply pending
adaptive-trust-ci migration-status   # exit 1 if pending
adaptive-trust-ci doctor             # ping + pending count
```

Compose production: `migrate` service uses `TRUST_CI_API_IMAGE`, command `["migrate"]`, `restart: "no"`, `depends_on postgres healthy`. API and worker `depends_on migrate completed_successfully`.

`PostgresStore.migrate(sql)` still exists and can execute arbitrary SQL **outside** the checksum registry. CLI does not use it. Leave it unused.

`pyproject.toml` packages `adaptive_trust_ci = ["resources/*.sql"]`. The API image copies `src` only; `trust-ci/sql/` is the operator-visible twin, not what the container applies.

Unit coverage (`test_migrations.py`): order, checksum, duplicate version, version gaps, pending plan, checksum drift, applied-but-missing-from-package. No live-DB migration test except `test_migration_registry_is_current_and_idempotent`.

## 4. Store contract (`PostgresStore`)

`trust-ci/src/adaptive_trust_ci/store.py`. One `psycopg` connection per call, `autocommit=False`, default `READ COMMITTED`, `dict_row`. No pool, no `statement_timeout`, no forced `sslmode`.

| operation | durability rule |
| --- | --- |
| `enqueue` | cancel other active heads for same `(repository, pr_number)`; `INSERT … ON CONFLICT (idempotency_key) DO NOTHING`; return existing row if conflict |
| `cancel_pr` | active → `cancelled` / `pull-request-closed` |
| `claim` | `trust_ci_claim_job` |
| `mark_running` / `heartbeat` / `finish` / `retry` | owner + live status + `lease_expires_at >= python now` |
| `record_approval` | unique `(approval_id, nonce)`; SQLSTATE `23505` → `ReplayError`; API maps to HTTP 409 |
| `has_valid_approval` | exact repo/PR/base/head/policy/scope and `issued_at <= now < expires_at` |
| `requeue_for_approval` | `needs_approval` → `queued` for exact `(repository, head_sha)` |
| `record_attestation` | unique `job_id` and `attestation_id`; `23505` → `ReplayError` |
| `get_attestation` | reconstruct `AttestationEnvelope` from payload+signature |

Worker replay (not a unittest): `JobRunner` reads stored attestation before checkout and republishes the Check Run without rerunning PR code. That is the GitHub-publication-failure recovery path named in the runbook. Integration tests prove envelope survival across a new `PostgresStore` instance and offline `verify_attestation`, not the runner replay branch.

### MemoryStore vs PostgresStore drift (must not leak into live tests)

| rule | MemoryStore | PostgresStore |
| --- | --- | --- |
| expired at attempt limit | `failure_code='attempts-exhausted'` | `attempts-exhausted-after-worker-loss` |
| claim clock | Python `now=` | SQL `now()` |
| attempts table | none | inserted on claim, updated on finish/retry |
| heartbeat deny message | `worker does not own the job lease` | `worker does not own a live job lease` |

Live tests already assert the PostgreSQL failure code. Heartbeat tests match the substring `own`.

Clock split: heartbeat writes `python_now + lease_seconds`; claim expiry compares `lease_expires_at < sql_now()`. Skew between worker and PostgreSQL can expire a lease early or keep it alive past the worker’s view. Bound NTP on the CI host; do not mix clocks in new SQL.

## 5. How the live harness is implemented

### 5.1 `trust-ci/tests/test_postgres_integration.py`

Class skipped unless `TRUST_CI_TEST_DATABASE_URL` is non-empty.

- `setUpClass`: `PostgresMigrator.apply()`
- `setUp`: `TRUNCATE … RESTART IDENTITY CASCADE` on events/attestations/approvals/attempts/jobs (registry preserved)
- eight tests: migration idempotence, concurrent claim, lease reclaim, heartbeat owner, attempt-limit dead, webhook idempotency, nonce replay, attestation reconnect+verify

Concurrent claim uses a 3-party `threading.Barrier` (two workers + main). Exactly one non-`None` claim, `attempts == 1`.

Lease/dead tests mutate `lease_expires_at = now() - interval '1 second'` in SQL because `claim()` does not honor Python time.

Attestation durability: sign, `record_attestation`, new `PostgresStore(DATABASE_URL)`, `get_attestation`, `verify_attestation` with the same public key.

Not covered in this file (covered only in MemoryStore or runner tests): `retry` → dead, `cancel_pr`, `requeue_for_approval`, `has_valid_approval` expiry, second `record_attestation` unique conflict, GitHub-outage attestation replay, `trust_ci_events` writes.

### 5.2 `trust-ci/scripts/postgres-integration.sh`

Disposable Compose project `adaptive-trust-ci-pgtest-${USER:-ci}-$$`.

```text
trap cleanup EXIT
docker compose -f trust-ci/compose.test.yaml up --build \
  --abort-on-container-exit --exit-code-from postgres-integration \
  postgres-integration
```

Cleanup: `down --volumes --remove-orphans`. Proved by `test_postgres_integration_runner_cleans_up_after_itself` (script text only).

### 5.3 `trust-ci/tests/postgres_restart_probe.py`

Not a `unittest.TestCase`. CLI `seed|verify`.

- `seed`: migrate, enqueue PR 799 with fixed SHAs (`9*40` / `8*40`) and policy digest `7*64`, print `job_id`
- `verify`: `ping()`, `get_job_for_sha`, fail if job missing or `base_sha`/`policy_digest` changed

### 5.4 `trust-ci/scripts/postgres-restart-drill.sh`

Same `compose.test.yaml`, distinct project name `…-pgrestart-…`. Sequence: up postgres-test → seed via `postgres-integration` image → `compose restart postgres-test` → wait healthy → verify. Prints `postgres restart drill: PASS`.

Data is on tmpfs (`/var/lib/postgresql/data`, 512m). `restart` keeps the container filesystem; `down --volumes` (trap on EXIT) destroys it after the drill. Do not use `up --force-recreate` here or the seed will vanish.

### 5.5 `trust-ci/compose.test.yaml`

```text
postgres-test:
  image: ${TRUST_CI_POSTGRES_IMAGE:?set immutable postgres image name@sha256 digest}
  POSTGRES_DB/USER=trust_ci_test
  POSTGRES_PASSWORD=trust_ci_test_password
  tmpfs data dir, pg_isready healthcheck, network trust-ci-test

postgres-integration:
  build Dockerfile.test with PYTHON_BASE_IMAGE pin
  image ${TRUST_CI_TEST_BUILD_TAG:-adaptive-trust-ci-test:2.1.0}
  TRUST_CI_TEST_DATABASE_URL=postgresql://trust_ci_test:trust_ci_test_password@postgres-test:5432/trust_ci_test
  command: python3 -m unittest -v tests.test_postgres_integration
```

Default test image tag is mutable (`:2.1.0`). That is acceptable for a disposable harness; production Compose forbids `build:` and requires digest-pinned prebuilt images (`test_production_compose_uses_prebuilt_images_and_isolated_dind`).

### 5.6 `trust-ci/compose.yaml` (production data path)

- postgres volume `trust-ci-postgres` (durable, not tmpfs)
- migrate job then api/worker
- postgres healthcheck `pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB`
- no SQL init scripts mounted; schema comes only from the migrate container

## 6. Env vars

### Live tests / drills

| variable | role | missing behavior |
| --- | --- | --- |
| `TRUST_CI_TEST_DATABASE_URL` | unittest + restart probe | class skip / probe `SystemExit` |
| `TRUST_CI_POSTGRES_IMAGE` | test+prod postgres image | Compose interpolation error |
| `TRUST_CI_PYTHON_BASE_IMAGE` | Dockerfile.test / build | Compose interpolation error |
| `TRUST_CI_TEST_BUILD_TAG` | optional local test image name | default `adaptive-trust-ci-test:2.1.0` |

### Production data plane

| variable | where | notes |
| --- | --- | --- |
| `TRUST_CI_DATABASE_URL` | `common.env`, `CommonSettings` | required; migrator/store/doctor |
| `POSTGRES_DB/USER/PASSWORD` | `postgres.env` | required by the postgres container |
| `TRUST_CI_BACKUP_DIR` | backup service | custom-format dump destination |
| `TRUST_CI_BACKUP_DATABASE_LABEL` | backup | label in SHA-256 manifest |
| `TRUST_CI_RESTORE_DATABASE_URL` | restore-drill | must be a disposable database |
| `TRUST_CI_COMPOSE_DIRECTORY` | backup.env.example | host compose path |

Related but not schema: `TRUST_CI_POLICY_PATH`, `TRUST_CI_PUBLIC_BASE_URL`, kill switch, API webhook/read token, worker signing key and GitHub App credentials, `TRUST_CI_RUNNER_IMAGE` (must be `name@sha256:` or `sha256:`).

Test DSN is cleartext password on a bridge network. Production example DSN also has no `sslmode`; backup code allows `sslmode` in the query string. For any non-Compose managed PostgreSQL, require `sslmode=require` (or stricter) in `TRUST_CI_DATABASE_URL`.

## 7. Image digest pins

`trust-ci/.env.example` (Compose interpolation only; do not commit a filled `.env`):

```text
TRUST_CI_PYTHON_BASE_IMAGE=python:3.12-slim-bookworm@sha256:REPLACE_WITH_BASE_DIGEST
TRUST_CI_POSTGRES_IMAGE=postgres:17.6-bookworm@sha256:REPLACE_WITH_POSTGRES_DIGEST
TRUST_CI_DIND_IMAGE=docker:29-dind-rootless@sha256:REPLACE_WITH_DIND_DIGEST
TRUST_CI_API_IMAGE=registry.example.com/adaptive-trust-ci-api@sha256:REPLACE_WITH_API_DIGEST
TRUST_CI_WORKER_IMAGE=registry.example.com/adaptive-trust-ci-worker@sha256:REPLACE_WITH_WORKER_DIGEST
TRUST_CI_RUNNER_IMAGE=registry.example.com/adaptive-trust-ci-runner@sha256:REPLACE_WITH_RUNNER_DIGEST
```

`WorkerSettings` and policy sandbox require an immutable runner digest at process start. Postgres/API/worker/dind pins are enforced by Compose `${VAR:?…}` and by `test_ops.py` string asserts, not by Python settings.

Plan doc says “PostgreSQL 16”; Compose example is `postgres:17.6-bookworm`. Pin 17.6 (or document a deliberate 16 pin) before deploy. Do not float `postgres:latest`.

Handoff step 3 still needs real digests, policy digest, SBOM, vuln scan, CI public key, holdout digest. Those are not in the tree.

## 8. Query-plan and index impact

Expected volume: one durable job per `(repository, PR, head SHA, policy digest)`, a handful of attempts (`max_attempts` default 3, policy cap 20), approvals per protected SHA, one attestation per finished job. No partitioning or retention job exists.

Claim shape:

```sql
WHERE attempts < max_attempts
  AND (status = 'queued'
       OR (status IN ('leased','running') AND lease_expires_at < now()))
ORDER BY created_at
FOR UPDATE SKIP LOCKED
LIMIT 1
```

Planner will typically use `trust_ci_jobs_queue_idx` for the queued arm and `trust_ci_jobs_lease_expiry_idx` for reclaim. The `OR` prevents a single perfect index; at this volume that is acceptable. `SKIP LOCKED` avoids wait-for-lock convoy.

Hot-path lookups:

- `get_job` PK
- `get_job_for_sha` → `trust_ci_jobs_head_idx`
- `has_valid_approval` → `trust_ci_approvals_lookup_idx`
- `get_attestation` unique `job_id`
- enqueue conflict unique `idempotency_key`
- nonce unique index

`002` first apply takes a `ShareLock` on live tables (`CREATE INDEX`, not `CONCURRENTLY`). On an empty or small P0 database this is seconds, not a migration outage. Do not add `CONCURRENTLY` inside the transactional migrator (it cannot run in a transaction).

Metrics snapshot (`_postgres_snapshot`) is five aggregate counts + oldest queued age, `ROLLBACK` so it never writes. `GROUP BY status` is cheap. `expired_leases` uses the lease partial index. No high-cardinality labels (repository/SHA/job id are excluded from Prometheus output).

`sql-safety` (`verification.py`) flags `DROP TABLE/DATABASE/SCHEMA`, `TRUNCATE TABLE`, unbounded `DELETE`/`UPDATE`. Current `001`/`002` do not match. Test `TRUNCATE` is in `.py`, so it does not trip the check. Policy `database` scope globs `**/*.sql` and `**/sql/**`; schema edits require a human-signed Trust CI approval on the exact SHA.

## 9. Failure modes

| failure | observed behavior | recovery |
| --- | --- | --- |
| missing `TRUST_CI_TEST_DATABASE_URL` | 8 tests skipped; handoff not satisfied | start disposable postgres, export DSN, rerun |
| missing digest-pinned compose images | compose refuses to start | set `.env` name@sha256 values |
| two workers, one queued job | one claim, `attempts=1` | expected |
| live lease, second claim | `NULL` | wait for expiry or owner finish |
| expired lease, attempts remaining | second worker reclaims, `attempts+=1` | expected |
| expired lease, attempts exhausted | `dead` / `attempts-exhausted-after-worker-loss`; claim returns `NULL` | no automatic resurrect |
| heartbeat from non-owner or expired | `RuntimeError` “does not own a live job lease”; `LeaseKeeper` surfaces it | lease expiry + reclaim |
| duplicate webhook identity | same `job_id`, `created=false` | expected |
| replayed approval nonce or id | unique violation → `ReplayError` → HTTP 409 | new nonce/id |
| second attestation for same job | `ReplayError` | runner replays stored envelope |
| checksum drift / edited historical SQL | `MigrationError`, migrate aborts | restore package or restore DB; never edit applied files |
| pending migrations | `migration-status` exit 1; doctor fail | run `migrate` |
| postgres down | `/health/ready` 503; worker `ping` fails closed | restart postgres; leases expire and reclaim |
| postgres restart (tmpfs test) | probe must still see seeded job | `postgres-restart-drill.sh` |
| postgres restart (prod volume) | jobs/approvals/attestations survive | reclaim expired leases; replay attestations |
| worker crash mid-run | lease expires; another worker claims or dead-letters | bounded by `max_attempts` |
| infrastructure error in worker | `retry` → `queued` or `dead` / `infrastructure-attempts-exhausted` | not in live integration file |
| kill switch | API 503, worker does not claim | does not mutate rows |
| concurrent two new heads for one PR | READ COMMITTED: both inserts can commit; both stay active | residual; needs advisory lock or partial unique index |
| clock skew worker vs postgres | heartbeat vs claim disagree | NTP; prefer SQL `now()` in heartbeat too |
| `CREATE OR REPLACE FUNCTION` later edit in 001 | will not apply | new migration `003_*` |
| events table empty | no audit row for replay/dead | residual vs design |
| restore without `--confirm-disposable` | restore-drill refuses | explicit disposable DSN |
| `sql-safety` on future `DROP`/`TRUNCATE TABLE` | verify fail | human-signed destructive-migration approval |

## 10. Backfill, locks, rollback, isolation

- **Backfill:** none. No historical jobs. Stop condition: not applicable.
- **Lock risk of 001/002:** advisory xact lock + DDL on empty DB. Function replace is not a table rewrite. No `ACCESS EXCLUSIVE` table rewrite.
- **Destructive SQL:** none in numbered migrations. Human-signed approval required before any future `DROP`/`TRUNCATE` of durable tables.
- **Rollback:** restore custom dump to a disposable DB (`restore-drill.sh`), verify SHA-256 manifest, then restore primary only under explicit operational grant. Service rollback is previous image+policy+holdout; that changes the policy epoch and invalidates old approvals/jobs.
- **Tenant isolation:** repository string allowlist in policy, not a DB tenant id. One PostgreSQL database holds all allowed repositories. No row-level security.
- **Sensitive data:** signatures, approval payloads, command stdout/stderr tails inside `jobs.result` (public job endpoint strips tails). Attestation payloads store hashes, not full logs. Backup dumps contain all of it; store dumps away from CI/GitHub/human private keys.
- **Reconciliation:** expired-lease metric; doctor migrations; `/health/ready` ping; attestation unique key; runner replay of stored envelope. No outbox table. GitHub Check Run publication is best-effort after durable attestation insert; crash between insert and publish is recovered by replay on next claim.

## 11. Validation queries (operator)

After migrate:

```sql
SELECT version, name, sha256, applied_at
FROM trust_ci_schema_migrations
ORDER BY version;
-- expect 001 schema, 002 operational_indexes, pending=0
```

After integration:

```sql
SELECT status, count(*) FROM trust_ci_jobs GROUP BY status;
SELECT count(*) FROM trust_ci_jobs WHERE status IN ('leased','running') AND lease_expires_at < now();
SELECT count(*) FROM trust_ci_approvals;
SELECT count(*) FROM trust_ci_attestations;
```

Stop conditions for any future data job: bounded `LIMIT`, keyed resume on `job_id`, abort if `trust_ci_schema_migrations` checksums drift, abort if kill switch is on.

## 12. What the implementation wave must do (data plane)

This agent does not implement. Facts for the later write owner:

1. Reproduce baseline, then actually run:
   - `trust-ci/scripts/postgres-integration.sh` (needs digest-pinned `TRUST_CI_POSTGRES_IMAGE` and `TRUST_CI_PYTHON_BASE_IMAGE`)
   - `trust-ci/scripts/postgres-restart-drill.sh`
   Capture output; skipped tests do not satisfy the handoff.
2. Fix stale `--exit-code-from tests` in README and `engineering/runbooks/trust-ci-rollout.md` to `postgres-integration`.
3. Decide PostgreSQL major (16 vs 17.6) and pin a real sha256.
4. Do not add GitHub Actions. Do not replace PostgreSQL with JSON/SQLite.
5. Optional hardening (not required to start the live suite, record as residual if deferred):
   - serialize enqueue per `(repository, pr_number)` or add `UNIQUE (repository, pr_number) WHERE status IN ('queued','leased','running','needs_approval')`
   - write `trust_ci_events` on claim/dead/replay
   - use SQL `now()` inside heartbeat or pass a single clock
   - `sslmode=require` on non-local DSNs
   - drop unused `PostgresStore.migrate`

## 13. Sources inspected

- `GROK_BUILD_HANDOFF.md` §2 required scenarios
- `docs/superpowers/specs/2026-08-23-trust-ci-control-plane-design.md`
- `docs/superpowers/plans/2026-08-23-trust-ci-control-plane.md`
- `trust-ci/sql/001_schema.sql`, `trust-ci/sql/002_operational_indexes.sql`
- `trust-ci/src/adaptive_trust_ci/resources/*.sql`
- `trust-ci/src/adaptive_trust_ci/{migrations,store,lease,settings,cli,api,worker,runner,backup,metrics,models}.py`
- `trust-ci/tests/{test_postgres_integration,postgres_restart_probe,test_migrations,test_store,test_ops,test_metrics}.py`
- `trust-ci/scripts/{postgres-integration,postgres-restart-drill,restore-drill}.sh`
- `trust-ci/{compose.test.yaml,compose.yaml,compose.build.yaml,Dockerfile.test,Dockerfile.api,pyproject.toml,.env.example}`
- `trust-ci/env/*.example`, `trust-ci/README.md`, `engineering/runbooks/trust-ci-rollout.md`
- `engineering/reviews/trust-ci-p0-local-verification.md`

No `.env` or credential files were read.
