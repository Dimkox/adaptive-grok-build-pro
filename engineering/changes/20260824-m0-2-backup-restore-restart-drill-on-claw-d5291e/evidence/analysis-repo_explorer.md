# Analysis — live Trust CI backup / restore / restart surface (M0.2)

Read-only map on host claw. No PEM, `.env`, or live-volume restore. No `compose down -v` on project `adaptive-trust-ci`.

## 1. Git / PR dirt

| Ref | SHA |
| --- | --- |
| `HEAD` (`milestone/m0-live-trust-authority`) | `ce03c87b3d9b8767105c01270869e33b50af56df` |
| `origin/milestone/m0-live-trust-authority` | `ce03c87b3d9b8767105c01270869e33b50af56df` (in sync) |
| `origin/main` | `48cb9737fac7f26fb70b425957a3ed64d4c1eb55` |
| PR **#5** head | `ce03c87b3d9b8767105c01270869e33b50af56df` (`milestone/m0-live-trust-authority`, OPEN) |

Working tree is **dirty**. Product `trust-ci/` is not in the dirty set.

| Change package | Kind | Notes |
| --- | --- | --- |
| `20260824-m0-2-sha-change-invalidation-on-draft-pr-5-beee95` | **uncommitted evidence** | `M state.json`; untracked `evidence/{code-review,implementation,sha-invalidation,test-review}.md` |
| `20260823-user-query-…-9d97f8` | leftover | `M state.json` only |
| `20260824-user-query-…-37bf04` | leftover | untracked directory |
| `20260817-user-query-…-33e0c2` | leftover | untracked directory |
| `20260824-m0-2-backup-restore-restart-drill-on-claw-d5291e` | this change | untracked package (this file) |

Do not mix leftover 9d97f8 / 37bf04 / 33e0c2 or beee95 evidence into this drill’s commits unless the write owner explicitly scopes it.

## 2. Compose project `adaptive-trust-ci` — live health

`trust-ci/compose.yaml` `name: adaptive-trust-ci`. Observed containers:

| Container | Status | Health |
| --- | --- | --- |
| `adaptive-trust-ci-postgres-1` | Up ~2h | **healthy** |
| `adaptive-trust-ci-api-1` | Up ~2h, `127.0.0.1:18080->8080/tcp` | **healthy** |
| `adaptive-trust-ci-worker-1` | Up ~1h | **no compose healthcheck** (`health=none`); process running |

`GET http://127.0.0.1:18080/health/ready` → **HTTP 200**

```json
{"status":"ready","policy_digest":"6737355947c21eb561073cb506ebc5698afd170088a34f8eaace50007c57d1a5","status_context":"adaptive-trust-ci/verified","active_approval_keys":1,"status_publisher":"worker-github-app"}
```

### Named volume for live postgres

Compose key: `trust-ci-postgres` → Docker name **`adaptive-trust-ci_trust-ci-postgres`**.

- Driver: `local`
- Mount: container `/var/lib/postgresql/data` (type `volume`, not tmpfs)
- Also bind: `./postgres/init` → `/docker-entrypoint-initdb.d` (ro init scripts)
- Labels: compose project `adaptive-trust-ci`, volume `trust-ci-postgres`

Sibling named volumes (do not delete): `adaptive-trust-ci_trust-ci-docker-data`, `adaptive-trust-ci_trust-ci-workspaces`.

## 3. Backup CLI / scripts / systemd

**CLI:** `trust-ci/src/adaptive_trust_ci/cli.py` (`prog=adaptive-trust-ci`), implementation `backup.py`.

| Command | Flags | Notes |
| --- | --- | --- |
| `backup-create` | `--output-dir PATH`, `--database-label` (required) | If `--output-dir` omitted: env **`TRUST_CI_BACKUP_DIR`** |
| `backup-verify` | `--dump`, `--manifest` (required) | SHA-256 + size |
| `backup-prune` | `--directory`, `--keep-last` (default 14), `--max-age-days` (default 30) | directory defaults to `TRUST_CI_BACKUP_DIR` |
| `restore-drill` | `--dump`, `--manifest`, **`--confirm-disposable`** | Requires env **`TRUST_CI_RESTORE_DATABASE_URL`**. `pg_restore --clean --if-exists` into that URL only. Refuses without `--confirm-disposable`. |

Dump filenames: `adaptive-trust-ci-{timestamp}.dump` plus sibling `.manifest.json` in the output dir.

**Default dump paths (docs / units, not live on claw):**

- Host example: `/srv/adaptive-trust-ci/backups` (`env/backup.env.example`)
- Inside backup unit bind: `/var/backups/adaptive-trust-ci`
- **Live host:** `/srv/adaptive-trust-ci/backups` **does not exist**; `/etc/adaptive-trust-ci/backup.env` **does not exist**

**Script:** `trust-ci/scripts/restore-drill.sh <backup.dump> <backup.manifest.json>`

- Requires disposable `TRUST_CI_RESTORE_DATABASE_URL`
- `docker compose -f trust-ci/compose.yaml run --rm --no-deps api backup-verify` then `api restore-drill --confirm-disposable`
- Mounts dump dir read-only as `/restore`
- Uses **live compose file** only as a **runner** for the `api` image; restore target must still be a **separate** URL, not the live DSN.

**Restart probe (test project, not live):** `trust-ci/scripts/postgres-restart-drill.sh`

- Project name: `adaptive-trust-ci-pgrestart-${USER}-$$`
- File: `compose.test.yaml`
- `down --volumes` **only** in EXIT trap for that **disposable** project
- Seed → `compose restart postgres-test` → verify via `tests.postgres_restart_probe`

**Systemd (in tree, not installed):**

- `trust-ci/systemd/adaptive-trust-ci-backup.service` — oneshot `docker compose run … api backup-create` then `backup-prune`
- `trust-ci/systemd/adaptive-trust-ci-backup.timer` — daily 02:17 UTC
- Host: units **not-found** / **inactive**; no `/etc/systemd/system/adaptive-trust-ci-backup.*`

## 4. Disposable restore database — does it exist now?

**No live disposable restore Postgres.**

`compose.test.yaml` defines:

- Service `postgres-test` (DB name `trust_ci_test`, user `trust_ci_admin_test`)
- Named volume key `trust-ci-pgtest-data` (would be `adaptive-trust-ci_trust-ci-pgtest-data` or a custom project prefix)
- Service `postgres-integration` (unittest image)

Observed:

- No container matching `postgres-test` / `pgtest` / `pgrestart` / restore
- `docker volume ls` has **no** `*pgtest*` / `*pgrestart*` volume
- Unrelated host DBs (`backup-postgres`, `postgres-db`, `domestos-pg`, `app-stack_postgres_data`) are **not** Trust CI restore targets

A restore drill must **create a new compose project** from `compose.test.yaml` (or equivalent throwaway container) and set `TRUST_CI_RESTORE_DATABASE_URL` to **that** instance. Do not point restore at live `postgres:5432/trust_ci`.

(Passwords exist in `compose.test.yaml` as test fixtures; they are not live production secrets and are not restated here.)

## 5. Restart drill: named volume vs tmpfs

`decisions.md` (2026-08-23): **`compose restart` discards tmpfs**. Restart proof needs a **named test volume** plus **`down --volumes` in the trap** so catalog survives restart and leftover data is cleaned.

| Stack | Data at `/var/lib/postgresql/data` |
| --- | --- |
| **LIVE** `adaptive-trust-ci` postgres | **Named volume `adaptive-trust-ci_trust-ci-postgres`** (not tmpfs). **Forbidden:** `docker compose -p adaptive-trust-ci down -v` / `--volumes` |
| **TEST** restart drill | Named volume `trust-ci-pgtest-data` on a **unique project name**; trap `down --volumes` is **allowed only there** |
| API/worker | tmpfs `/tmp` and `/home/trustci` only — unrelated to PG catalog |

Live restart of **the same postgres container** (`docker compose restart postgres` **without** `-v`) would keep the named volume. That is still an **operational interruption** of M0; prefer proving restart on **postgres-test**, not live.

---

## Safe drill vs forbidden (live `down -v`)

**Safe**

1. `backup-create` via `docker compose run --rm --no-deps api backup-create --output-dir <host-dir-not-live-volume> --database-label …` (read from live via backup role URL; write dumps to a **new host directory**, not into `adaptive-trust-ci_trust-ci-postgres`).
2. `backup-verify` on those dump+manifest files.
3. Stand up **throwaway** `compose.test.yaml` with a **unique `--project-name`**; wait for `postgres-test` healthy.
4. `restore-drill.sh` / `restore-drill --confirm-disposable` with `TRUST_CI_RESTORE_DATABASE_URL` pointing **only** at that throwaway DSN.
5. Restart drill: `postgres-restart-drill.sh` (trap `down --volumes` on the **pgrestart** project only).
6. Tear down **only** the throwaway project: `docker compose -p <pgrestart-or-restore-id> down --volumes`.

**Forbidden**

- `docker compose -p adaptive-trust-ci down -v` / `down --volumes` / `volume rm adaptive-trust-ci_trust-ci-postgres`
- `pg_restore` / `restore-drill` using the live database URL or any DSN that shares `adaptive-trust-ci_trust-ci-postgres`
- Restore into the live volume, even with `--confirm-disposable`
- Reading `.env`, PEM, `runtime/*-key.pem`, or printing live passwords
- Installing systemd backup by mutating `/etc` without a separate delegated grant
- Mixing leftover 9d97f8 / 37bf04 / 33e0c2 / uncommitted beee95 evidence into this drill’s product tree unless scoped
