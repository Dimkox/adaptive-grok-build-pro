# Architect ruling — host-local backup / restore / restart drill on claw

Route `d5291e6a1516`. Change `engineering/changes/20260824-m0-2-backup-restore-restart-drill-on-claw-d5291e`. Write owner: `general_implementer`. This agent does not compose-up, `down --volumes`, restore onto live Postgres, edit policy/holdout/PEM/overlay/tracked compose, protect `main`, push, merge, or print secrets.

Live (this turn, no secrets): project `adaptive-trust-ci`; `adaptive-trust-ci-postgres-1` healthy on volume `adaptive-trust-ci_trust-ci-postgres`; api healthy; worker up; `GET http://127.0.0.1:18080/health/ready` **200**; policy digest prefix `6737355947c2`; overlay `/home/pall/adaptive-trust-ci-host/compose.host-socket.yaml` mode `0600` untracked. Activation report cell **Backup/restore/restart drill = UNKNOWN**.

## Ruling (one paragraph)

**Run a three-step host-local drill against the already-running overlay stack. Do not treat live catalog as a restore TARGET.** (1) `backup-create` the live database as role `trust_ci_backup` into gitignored `trust-ci/runtime/backups/` with `--database-label adaptive-trust-ci-primary`. (2) `restore-drill --confirm-disposable` into a **throwaway** Postgres on network `adaptive-trust-ci_trust-ci` with **tmpfs** data (dbname `trust_ci_restore`, hostname ≠ `postgres`). (3) `docker compose -p adaptive-trust-ci restart postgres` (not `down`, not `--volumes`) and prove named volume + job count + `/health/ready` 200. Tracked `trust-ci/compose.yaml` and the host-socket overlay stay unchanged. This is **not** M0.2 complete and **not** merge authority.

## Conflicts resolved

| Source | Claim | Ruling |
| --- | --- | --- |
| User this turn | Host-local backup/restore/restart; live catalog is never the restore TARGET | **Wins.** |
| `trust-ci/scripts/restore-drill.sh` | Uses live `compose.yaml` `api` image | **Allowed** as the CLI runner (image has `pg_restore`). Disposable DSN is mandatory. |
| Runbook `Database backup` | `pg_dump` + `compose cp` to `./runtime/trust-ci.dump` | **Superseded for this drill** by CLI `backup-create` (manifest + sha256). Do not leave an unverified dump. |
| `postgres-restart-drill.sh` | Unique test project + `down --volumes` in trap | **Pattern for throwaway only.** Never `down --volumes` on project `adaptive-trust-ci`. |
| `decisions.md` 2026-08-23 | `compose restart` discards tmpfs; named volume proves catalog | **Stands.** Live already uses named volume `adaptive-trust-ci_trust-ci-postgres`. Restart live postgres; tmpfs is the restore throwaway, not the live data dir. |
| `compose.test.yaml` | Disposable `postgres-test` / `trust-ci-pgtest-data` | **Backup identity source (test passwords are tracked). Not required as restore host** — `Dockerfile.test` has no `postgresql-client`, so restore must run in the **api** image. |
| Prior M0.2 slices | Overlay stays untracked; no `branch-protect`; no public webhook | **Stands.** This slice does not claim M0.2 exit. |

---

## 1. backup-create (live is SOURCE only)

| Knob | Value |
| --- | --- |
| CLI | `adaptive-trust-ci backup-create` via `docker compose -p adaptive-trust-ci run --rm --no-deps api` |
| `--database-label` | `adaptive-trust-ci-primary` (matches `trust-ci/env/backup.env.example` `TRUST_CI_BACKUP_DATABASE_LABEL`) |
| Output dir | Host `trust-ci/runtime/backups/` (gitignored by `trust-ci/runtime/*`). Inside the container: `/var/backups/adaptive-trust-ci`. Create mode `0700`. **Not** the change package, **not** world-readable temp, **not** `/srv/...` unless that dir already exists as the operator destination. |
| Postgres identity | Role **`trust_ci_backup`** (SELECT-only; `003_database_roles.sql` / `postgres/init/001_roles.sh`). Same override as systemd `adaptive-trust-ci-backup.service`: `--env TRUST_CI_DATABASE_URL="$TRUST_CI_BACKUP_DATABASE_URL"`. Default api env is `trust_ci_api` and **must not** be used for dump. |
| Image | Live `api` service (has `postgresql-client`). `--no-deps` so compose does not touch postgres/worker. |

Do **not** Read / `echo` / `set -x` `trust-ci/env/*.env`, backup DSN, or passwords. Source `env/backup.env` in a `/tmp` helper with `set +x`, pass the override into `compose run`, print **only** the CLI JSON (`dump_path`, `manifest_path`, `sha256`, `size_bytes`), unlink the helper. If `backup.env` is absent, the helper may build `postgresql://trust_ci_backup:<urlencoded>@postgres:5432/trust_ci` from `TRUST_CI_BACKUP_DB_PASSWORD` the same way — still never print it.

Expected dump pair: `adaptive-trust-ci-<UTC>.dump` + `adaptive-trust-ci-<UTC>.manifest.json` mode `0600`. Abort if `size_bytes` is 0.

---

## 2. restore-drill (disposable TARGET only)

**Hard rule:** live volume `adaptive-trust-ci_trust-ci-postgres` is never a restore destination. `restore_drill()` refuses without `--confirm-disposable` and uses `pg_restore --clean --if-exists --exit-on-error`. Pointing that at live `trust_ci` would drop the catalog.

`restore-drill.sh` already passes `--confirm-disposable` and requires `TRUST_CI_RESTORE_DATABASE_URL`. It runs **live** `compose.yaml` `api` `--no-deps` on network `adaptive-trust-ci_trust-ci`. Therefore the throwaway Postgres must be **on that network** and reachable by a hostname **other than** `postgres`.

### Throwaway Postgres (preferred; smallest)

```text
Image: same digest as adaptive-trust-ci-postgres-1
        (postgres:17.6-bookworm@sha256:f3bd19c606… — from inspect Config.Image, not from .env)
Name:  adaptive-trust-ci-restore-throwaway-<pid>
Net:   adaptive-trust-ci_trust-ci
Data:  --tmpfs /var/lib/postgresql/data   (anonymous/tmpfs — NOT the live named volume)
DB:    POSTGRES_DB=trust_ci_restore
User:  POSTGRES_USER=trust_ci_restore_admin
```

Wait until `pg_isready` in that container. DSN host = throwaway **container name**; dbname = `trust_ci_restore`. Extra guards before `restore-drill.sh`:

- DSN host is **not** `postgres`, `adaptive-trust-ci-postgres-1`, `127.0.0.1`, or `localhost`
- DSN dbname is **not** `trust_ci`
- `docker inspect` throwaway Mounts do **not** include `adaptive-trust-ci_trust-ci-postgres`

Then:

```text
TRUST_CI_RESTORE_DATABASE_URL=<throwaway DSN> \
  trust-ci/scripts/restore-drill.sh \
  trust-ci/runtime/backups/<file>.dump \
  trust-ci/runtime/backups/<file>.manifest.json
```

The script always supplies `--confirm-disposable`. Do not invoke `restore-drill` without that flag. Do not print the DSN.

Cleanup: `docker rm -f` the throwaway only. **No** `compose down` on `adaptive-trust-ci`. `down --volumes` is forbidden on the live project; it is acceptable only if a unique-name `compose.test.yaml` project was used instead of tmpfs (trap pattern from `postgres-integration.sh`). Prefer tmpfs so live `down --volumes` is never in the command history of this slice.

`compose.test.yaml` `postgres-test` remains a valid alternative (volume `trust-ci-pgtest-data` under a unique `--project-name`, then `docker network connect adaptive-trust-ci_trust-ci <container>`). Test passwords in that file are tracked fixtures, not live secrets — still do not paste the DSN into evidence.

---

## 3. Restart drill (live named volume)

Live data dir is already a named volume (not tmpfs). Prove it survives container restart.

1. **Before:** job count via container env, no DSN printed:

   `docker exec adaptive-trust-ci-postgres-1 sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT count(*) FROM trust_ci_jobs"'`

   Optionally `SELECT job_id, status` (ids/status are operator-safe). Known job `1b63d10b-90c1-498a-97b8-7b5e0ea76aec` may still exist alongside later SHA-change jobs.

2. **Restart only postgres:** `docker compose -p adaptive-trust-ci restart postgres`  
   Equivalent: `docker restart adaptive-trust-ci-postgres-1`.  
   Do **not** `compose down`, `down --volumes`, `down -v`, or restart api/worker/overlay. Do **not** start `docker-engine`.

3. Wait until postgres healthy, then `GET http://127.0.0.1:18080/health/ready` → **200**. Ready may 503 while Postgres is down; that is expected. Do not flip the kill switch.

4. **After:** same `count(*)` (equal); volume `adaptive-trust-ci_trust-ci-postgres` still exists; `git diff --exit-code -- trust-ci/compose.yaml`.

`GET /jobs/{id}` needs `TRUST_CI_READ_TOKEN` — do not use it if that requires printing the token. Container-local `psql` is enough.

---

## 4. Tracked compose and overlay

| Item | Rule |
| --- | --- |
| `trust-ci/compose.yaml` | **Unchanged.** No sock, isolated DinD remains the tracked topology. |
| `trust-ci/compose.test.yaml` | **Unchanged.** |
| Overlay `compose.host-socket.yaml` | **Unchanged**, stays outside the git tree, mode `0600`. |
| Deployed `runtime/policy.json`, holdout, PEMs, `env/*.env` | **Unread and unedited.** |
| `main` protection | **Do not** `branch-protect`. |

No product CLI/schema change is required. Existing unit tests already lock `--confirm-disposable`, backup-role override, and restore JSON `status=restored-and-verified`.

---

## 5. Observe success without secrets

Record in `evidence/drill-report.md` (and activation-report cell) **only**:

| Signal | Pass |
| --- | --- |
| Dump size | `size_bytes` > 0 from `backup-create` JSON |
| Manifest digest | `sha256` **prefix 12 hex**; `backup-verify` `status=verified`; same prefix after restore |
| Restore JSON keys | `status`, `sha256`, `size_bytes`, `database_label`, `dump_path`, `manifest_path` with `status=restored-and-verified` and `database_label=adaptive-trust-ci-primary` |
| Job count | integer before = integer after postgres restart |
| Ready | `curl -fsS -o /dev/null -w '%{http_code}' http://127.0.0.1:18080/health/ready` → `200` (body may include `status=ready` and digest prefix `6737355947c2`) |
| Volume | `adaptive-trust-ci_trust-ci-postgres` still listed |
| Compose | `git diff --exit-code -- trust-ci/compose.yaml` |

Do **not** paste DSN, passwords, PEM, webhook secret, read token, `compose config` output, env dumps, or full dump paths under `/srv` if they embed host secrets.

---

## 6. Forbidden

- `docker compose -p adaptive-trust-ci down --volumes` / `down -v` / `down` of the live project
- Restore DSN host `postgres` or dbname `trust_ci`
- Editing deployed policy, holdout, images, PEMs, `trust-ci/env/*.env`, tracked compose, overlay
- Reading `.env` / PEM / `trust-ci/runtime/*.pem` into chat or git
- `branch-protect` / protecting `main`
- Forging Check Runs, GitHub Actions, public webhook registration
- Copying dump bytes into the change package
- Claiming M0.2 complete

---

## Smallest coherent sequence

0. Preflight: ready 200; volume `adaptive-trust-ci_trust-ci-postgres` present; overlay still untracked; kill switch off; compose.yaml clean.
1. Snapshot `trust_ci_jobs` count (integer only).
2. `backup-create` → `trust-ci/runtime/backups/` label `adaptive-trust-ci-primary` as `trust_ci_backup`.
3. Start tmpfs throwaway Postgres on `adaptive-trust-ci_trust-ci`; confirm mounts ≠ live volume.
4. `restore-drill.sh` with `TRUST_CI_RESTORE_DATABASE_URL` + `--confirm-disposable` (script-supplied).
5. `docker rm -f` throwaway only.
6. `docker compose -p adaptive-trust-ci restart postgres`; wait healthy; ready 200; job count unchanged.
7. Write `evidence/drill-report.md` with the operator-safe table. Set activation-report **Backup/restore/restart drill** to `2026-08-24 pass` (host-local). Leave public webhook / `main` protection / policy retitle untouched.

**Stop.** Do not install the systemd backup timer in this slice. Do not prune live backups (`backup-prune`) unless the output dir was created solely for this drill and contains only this pair.

## Grants

User named this operational drill. Compose restart/backup/restore are **not** `grok_approve.py` production actions (`git-push-branch` etc.). Mint **no** production grant. If a later docs commit touches `decisions.md` / `AGENTS.md`, that is a separate `protected-path-write` after the last local write. Do not mint `git-push-branch` unless the user explicitly asks to push this evidence.

## Rollback

Throwaway: `docker rm -f` (tmpfs vanishes). Live: if postgres does not come back, `docker compose -p adaptive-trust-ci start postgres` or `up -d postgres` **without** `--volumes`. Catalog remains on `adaptive-trust-ci_trust-ci-postgres`. A failed restore on throwaway does not touch live. If ready stays 503, check kill-switch file is absent; do not recreate STOP.

## Acceptance (this slice only)

- Fresh integrity-checked dump of live catalog in gitignored runtime; label `adaptive-trust-ci-primary`
- Restore proven only on disposable tmpfs Postgres with `--confirm-disposable`
- Live postgres restarted; named volume and job count survive; `/health/ready` 200
- Tracked compose.yaml and overlay unchanged; `main` unprotected; no secrets in git/chat
- Activation-report drill cell filled; M0.2 remainder stays open
