# data_architect — api+worker recreate vs PostgreSQL catalog

Route `01096425a38d`. Change `20260824-m0-2-public-tls-edge-apache-trust-ci-ii-tonya-ru-010964`.
Agent: `data_architect` (read-only except this report). Skills: `/adaptive-delivery`, `data-change`.
No `.env`, no credentials, no live SQL, no dump contents.

## Verdict

**No.** Recreating `api` and `worker` with the named-service Compose command does **not** lose PostgreSQL state.

Catalog and jobs live only in PGDATA on the project-prefixed named volume `adaptive-trust-ci_trust-ci-postgres`. `api` and `worker` do not mount that volume. `TRUST_CI_PUBLIC_BASE_URL` is process env (`common.env`), not a column.

Allowed command (exact service list):

```bash
docker compose \
  -f compose.yaml \
  -f "$HOST_SOCKET_OVERLAY" \
  up -d --force-recreate api worker
```

**Must not** name `postgres`. **Must not** `down` the project. **Must not** `down -v` / `--volumes`. Whole-project teardown is forbidden this slice even without `-v`.

No schema or migration in this slice. Backup/restore/restart drill already **2026-08-24 pass**; do not re-run unless the recreate itself fails.

## 1. Where state lives

`trust-ci/compose.yaml` sets `name: adaptive-trust-ci`.

| Compose volume key | Docker volume name | Mount | Holds |
| --- | --- | --- | --- |
| `trust-ci-postgres` | **`adaptive-trust-ci_trust-ci-postgres`** | `postgres` → `/var/lib/postgresql/data` | Operational catalog (jobs, attempts, approvals, attestations, events, `trust_ci_schema_migrations`) |
| `trust-ci-docker-data` | `adaptive-trust-ci_trust-ci-docker-data` | `docker-engine` DinD graph | Not catalog; overlay disables DinD this host |
| `trust-ci-workspaces` | `adaptive-trust-ci_trust-ci-workspaces` | tracked `worker` workspace dir | Scratch; overlay replaces with a host bind |

Postgres also bind-mounts `./postgres/init` read-only as `/docker-entrypoint-initdb.d`. Official image runs those scripts **only on empty PGDATA** (first boot). Recreating `api`/`worker` does not empty PGDATA and does not re-run init.

`api` volumes: policy + trust-store + `./runtime/control` bind. `tmpfs` `/tmp` and `/home/trustci` are discarded on recreate (not catalog).

`worker` tracked volumes: policy, holdout, signing/GitHub PEM binds, control bind, `trust-ci-workspaces`. Host overlay (`/home/pall/adaptive-trust-ci-host/compose.host-socket.yaml`) overrides **worker / runner-loader / docker-engine only**. It does not mention `postgres` or `trust-ci-postgres`.

Source of operational truth: PostgreSQL. No Elasticsearch/OpenSearch, no ClickHouse, no search projection, no backfill.

Packaged schema (unchanged this slice): `001_schema.sql`, `002_operational_indexes.sql`, `003_database_roles.sql` plus migrator registry `trust_ci_schema_migrations`. No `004_*.sql`.

`TRUST_CI_PUBLIC_BASE_URL` is loaded in `CommonSettings` from the environment. Changing it in untracked `env/common.env` requires new `api`/`worker` containers (env_file is applied at create). Postgres `env_file` is `env/postgres.env` only — URL change is not a postgres config change.

## 2. Why named-service `--force-recreate` keeps the catalog

Compose v2 `up -d --force-recreate api worker`:

- Recreates **only** the listed services.
- Starts dependencies if they are not already in the required state; it does **not** force-recreate them unless `--always-recreate-deps` is set.
- Does not delete named volumes.
- Does not publish or wipe `5432`.

Dependency chain from tracked compose:

- `api` → `migrate` (`service_completed_successfully`)
- `worker` → `migrate` (same) and `runner-loader`
- `migrate` → `postgres` (`service_healthy`)

If `postgres` is already healthy and `migrate` already exited 0, they stay. If `migrate` is missing, Compose may re-run the oneshot. That is safe here: migrations are checksum-locked and pending is empty; this slice adds no SQL. Do **not** add `--always-recreate-deps` (would pull postgres into recreate). Do **not** list `postgres` or `migrate` on the command.

`postgres` init (`001_roles.sh`) is first-boot only. A running volume keeps roles, ACLs, and rows.

Worker recreate may drop an in-flight lease owner; rows remain. `trust_ci_claim_job` reclaims expired leases or marks attempt-exhausted jobs `dead`. That is designed recovery, not catalog loss. GitHub webhook retries are the HTTP path; HMAC/approval tables stay in Postgres.

## 3. Forbidden: whole-project down / wrong recreate order

**Forbid** these this slice:

| Command / order | Why data is at risk |
| --- | --- |
| `docker compose down` (whole project) | Stops and **removes** `postgres` container. Named volume usually survives, but next `up` recreates postgres, re-runs `migrate`, and drops all in-flight leases. Easy to add `-v` by habit. Prior M0 drill decision: live project was **not** `down`. |
| `docker compose down -v` / `down --volumes` | **Destroys** `adaptive-trust-ci_trust-ci-postgres`. Next start is empty PGDATA; init recreates roles; catalog/jobs **gone**. |
| `docker volume rm adaptive-trust-ci_trust-ci-postgres` | Same as `-v` for the catalog. |
| `up -d --force-recreate` with **no** service names | Recreates **postgres** too. Volume may persist, but this is unnecessary restart of the source of truth for an env-URL change. |
| `up -d --force-recreate api worker postgres` | Names postgres. Forbidden. |
| `--always-recreate-deps` | Can recreate postgres because `api` depends on `migrate` depends on `postgres`. |
| Restore-drill / `pg_restore --clean` into live hostname `postgres` / live dbname | Destructive. Drill target is throwaway tmpfs (`trust_ci_restore`, hostname not `postgres`). Volume is dump **source** and `compose restart postgres` **subject**, never restore TARGET (`decisions.md` 2026-08-24). |

If operators need to bounce listeners only: the allowed `up -d --force-recreate api worker` (plus the same untracked overlay). Prefer that over `restart` after `common.env` change, because env_file is not re-read by `restart`.

`compose restart postgres` without `-v` was the passed drill; it is **not** required to apply the public URL.

## 4. No schema / migration this slice

This change is DNS + Apache TLS reverse proxy + `TRUST_CI_PUBLIC_BASE_URL=https://trust-ci.ii-tonya.ru`.

Do not:

- add or edit `trust-ci/sql/*.sql` or `adaptive_trust_ci/resources/*.sql`
- run `migrate` as a targeted recreate
- `ALTER` / `DROP` / unbounded SQL
- backfill
- change indexes, roles, or `trust_ci_claim_job`

Human gate `migration_or_external_write_approval` is **not** a SQL migration gate for this slice (there is no schema change). It does not authorize `down -v` or live restore.

## 5. Backup drill — already passed; when to touch it

Activation report and plan: **2026-08-24 pass** — `backup-create` / `backup-verify` / restore-drill `--confirm-disposable` on throwaway tmpfs; `compose restart postgres` without `-v`; jobs 2=2; `/health/ready` 200.

On-disk evidence (not re-read as SQL): `trust-ci/runtime/backups/adaptive-trust-ci-20260824T122558Z.dump` plus manifest `schema_version: 1`, `database_label: adaptive-trust-ci-primary`, `size_bytes: 26496`, dump sha256 `c46da2cb97547234c23e7a1113de46bd875ab3963681dc9c3081a1fefcf11a1f`. Dump bytes were not opened.

**Do not re-run the drill** for the TLS-edge recreate.

Re-run **only if** the allowed `api`/`worker` recreate fails in a way that suggests catalog damage (postgres unhealthy, empty relations, `/health/ready` never returns after listeners are up). Then:

1. Confirm volume still exists; **do not** `down -v`.
2. `backup-verify` the existing dump (read-only).
3. Restore-drill only to a disposable URL (`--confirm-disposable`); hostname must not be live `postgres`.
4. Do not `pg_restore --clean` onto `adaptive-trust-ci_trust-ci-postgres`.

CLI restore already requires `--confirm-disposable` and `TRUST_CI_RESTORE_DATABASE_URL`. That flag is not a substitute for choosing a throwaway host/db.

## 6. Post-recreate data checks (no live SQL from this agent)

After the allowed command, operators may use HTTP only:

- `GET http://127.0.0.1:18080/health/ready` → ready
- existing job/Check Run identities in the activation report remain the same rows (`external_id` / job id `1b63d10b-90c1-498a-97b8-7b5e0ea76aec` and later SHA-change job). Do not expect those UUIDs to vanish.
- unsigned public POST `/webhooks/github` → 401 (HMAC), not a new schema.

Do not `psql` the live database for this slice. Do not count jobs via SQL from agents.

## Ruling for implementers

1. Recreate **`api worker` only**, same host-socket overlay, no postgres in the argv, no `down`, no `-v`.
2. Catalog and jobs survive on `adaptive-trust-ci_trust-ci-postgres`.
3. Whole-project down is forbidden (data-at-risk path).
4. No migration files, no live restore, no new backup drill unless recreate fails.
5. Apache/TLS/DNS are outside the volume; they do not rewrite PGDATA.
