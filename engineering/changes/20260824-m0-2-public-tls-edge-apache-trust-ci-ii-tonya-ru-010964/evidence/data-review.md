# data_review — postgres catalog vs TLS-edge work

Route `01096425a38d`. Change `20260824-m0-2-public-tls-edge-apache-trust-ci-ii-tonya-ru-010964`.
Agent: `data_reviewer` (read-only). No `.env`, no credentials, no live SQL.

## Verdict

**pass**

This slice did **not** recreate PostgreSQL, did **not** `compose down` / `down -v`, and the operational catalog volume is intact. Schema/migrations were not part of the change. `api`/`worker` `--force-recreate` (env URL) has **not** been run yet; Apache HTTP vhost only.

## Schema / query / backfill

| Item | Finding |
| --- | --- |
| Versioned SQL | Unchanged. Packaged `001`–`003` only; no `004`. |
| Destructive migration | None. Human gate is host DNS/Apache/certbot/ufw/env, not SQL. |
| Backfill | None. No ClickHouse/ES. Source of truth remains PostgreSQL. |
| Query-plan / indexes | N/A this slice. |

## Postgres was not recreated

Live inspect `adaptive-trust-ci-postgres-1` (no SQL):

| Field | Value |
| --- | --- |
| Container ID | `6f442721d918` |
| Created | `2026-08-24T09:06:55Z` (same create as `api`/`migrate` first boot) |
| StartedAt | `2026-08-24T12:27:59Z` |
| RestartCount | `0` |
| Health | `healthy` |
| Image | `postgres:17.6-bookworm` (digest pinned) |
| Data mount | `adaptive-trust-ci_trust-ci-postgres` → `/var/lib/postgresql/data` |

`StartedAt` after `Created` matches the **2026-08-24 backup drill** `compose restart postgres` **without** `-v` (container identity preserved, RestartCount 0, volume not replaced). That is a restart, not a recreate.

This TLS-edge implementation (`evidence/implementation.md`) states overlay untouched and postgres not recreated. Compose argv for the remaining URL step remains **named services only**: `up -d --force-recreate api worker` plus host-socket overlay. Postgres is not in argv.

## No `down -v`

| Signal | Evidence |
| --- | --- |
| Named volume still present | `adaptive-trust-ci_trust-ci-postgres` Created `2026-08-24T09:06:55Z`, driver `local` |
| Sibling volumes | `trust-ci-docker-data`, `trust-ci-workspaces` still listed |
| Project still up | `api` healthy loopback `127.0.0.1:18080`, `worker` Up 4h, `postgres` healthy, `migrate` Exited 0 |
| Forbidden commands | Not observed: `down`, `down -v`, `volume rm`, `--always-recreate-deps`, `force-recreate` without service names |

`down -v` would destroy PGDATA and force first-boot init. Volume create timestamp equals original project create; it was not deleted and re-created.

## Catalog intact (HTTP / volume, not SQL)

- `GET http://127.0.0.1:18080/health/ready` → `{"status":"ready",...}` with `status_publisher":"worker-github-app"` and `active_approval_keys":1`.
- Ready implies migrator/catalog path still answers; empty PGDATA would not stay ready with the existing image/policy.
- Data architect: catalog lives only on `adaptive-trust-ci_trust-ci-postgres`; `api`/`worker` do not mount it. Init scripts run only on empty PGDATA.
- Prior dump `trust-ci/runtime/backups/adaptive-trust-ci-20260824T122558Z.dump` remains on disk (schema_version 1). Not re-opened. No live restore.

Job UUID identity was not re-queried via SQL (forbidden for this agent). No evidence those rows were wiped.

## Recovery / rollback alignment

- Rollback (`rollback.md`): `a2dissite`, revert `TRUST_CI_PUBLIC_BASE_URL`, `force-recreate api worker` only. **Never** `compose down -v`.
- Requirements abort if recreate includes postgres or `down -v`.
- Restore-drill already passed on throwaway tmpfs; not re-run. Do not `pg_restore --clean` onto live hostname `postgres`.

## Residual (does not fail this review)

Public TLS and `TRUST_CI_PUBLIC_BASE_URL=https://trust-ci.ii-tonya.ru` are **not** applied yet (DNS A mismatch). When they are, the same rule holds: recreate **api worker** only; leave this postgres container and volume.

## Status for `grok_review.py`

`--status pass` — postgres not recreated, no `down -v`, catalog volume and `/health/ready` intact.
