# Pre-implementation analysis: backup / restore CLI (code_reviewer)

Change: `20260824-m0-2-backup-restore-restart-drill-on-claw-d5291e`  
Scope: read-only inspection of `adaptive_trust_ci` backup CLI, `backup.py`, and `restore-drill.sh`. No live restore. No secrets quoted.

## Commands in `cli.py`

Parser (`trust-ci/src/adaptive_trust_ci/cli.py`):

- `backup-create` — `--output-dir` (optional), `--database-label` required (`89:91:trust-ci/src/adaptive_trust_ci/cli.py`).
- `backup-verify` — `--dump`, `--manifest` required (`93:95`).
- `backup-prune` — `--directory` optional; `--keep-last` default 14; `--max-age-days` default 30 (`97:100`).
- `restore-drill` — `--dump`, `--manifest` required; `--confirm-disposable` store_true (`102:105`).

Dispatch:

- **backup-create** (`247:267`): `CommonSettings.load()` then `create_backup(settings.database_url, output_dir, database_label=…)`. Output dir is `--output-dir` or `TRUST_CI_BACKUP_DIR`.
- **backup-verify** (`269:271`): file SHA-256 / size only; no database URL.
- **backup-prune** (`273:281`): local files under backup dir; no DSN.
- **restore-drill** (`283:294`): target is **only** `TRUST_CI_RESTORE_DATABASE_URL`. Missing env → `SystemExit`. Then `restore_drill(..., confirm_disposable=args.confirm_disposable)`.

## Identity used for dump (read-only backup role?)

**Intended production identity:** PostgreSQL role `trust_ci_backup`.

- Init: `CREATE ROLE trust_ci_backup LOGIN … NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION` (`trust-ci/postgres/init/001_roles.sh` around 33–45).
- Grants: `GRANT SELECT ON ALL TABLES/SEQUENCES IN SCHEMA public TO trust_ci_backup` (`trust-ci/sql/003_database_roles.sql` 23–35). No INSERT/UPDATE/DELETE grants to that role (`test_database_roles.py` 37–38).
- Env template: `TRUST_CI_BACKUP_DATABASE_URL=postgresql://trust_ci_backup@…` (`trust-ci/env/backup.env.example`).
- Systemd oneshot remaps identity at runtime (`trust-ci/systemd/adaptive-trust-ci-backup.service` 11):  
  `docker compose run … --env TRUST_CI_DATABASE_URL="$TRUST_CI_BACKUP_DATABASE_URL" … api backup-create …`

**CLI itself does not hard-code the backup role.** `backup-create` always dumps `CommonSettings.database_url` (`TRUST_CI_DATABASE_URL`). If an operator runs `api backup-create` without the systemd override, the dump uses whatever identity the **api** container has (`trust_ci_api`), which is **not** SELECT-only. pg_dump still only reads; the extra risk is using a write-capable login, not a different dump format.

Credentials never appear on the `pg_dump` argv: `_service_environment` writes a 0600 `pg_service.conf` and sets `PGSERVICE` (`backup.py` 274–292, 295–318).

## Does restore-drill refuse without `--confirm-disposable`?

**Yes at the library boundary.** `restore_drill` (`backup.py` 199–208):

```
if not confirm_disposable:
    raise BackupError('restore drill requires --confirm-disposable for the target database')
```

Unit: `test_restore_requires_explicit_disposable_confirmation` (`trust-ci/tests/test_backup.py` 73–85).

**Shell wrapper always supplies the flag** (`trust-ci/scripts/restore-drill.sh` 36–39): after `backup-verify`, it runs `api restore-drill --dump … --manifest … --confirm-disposable`. There is no interactive prompt; passing the flag is mechanical once the script is invoked.

Direct CLI without the flag never reaches `pg_restore`.

## Can restore target the live DSN by mistake?

**Yes. Confirmation is operator honor; there is no DSN inequality check.**

Guards that exist:

1. Restore URL is a **different env var** than the live API/worker URL (`TRUST_CI_RESTORE_DATABASE_URL` vs `TRUST_CI_DATABASE_URL`). CLI will not silently restore into `settings.database_url`.
2. Script requires the restore URL to be set (`restore-drill.sh` 9).
3. `--confirm-disposable` must be true.
4. Dump/manifest must sit in the same directory; dump volume is mounted `:ro` (`restore-drill.sh` 16–28).

Guards that **do not** exist:

- No comparison of restore host/port/dbname against live `TRUST_CI_DATABASE_URL`.
- No hostname allowlist (`localhost` only), no name pattern (`*_drill`, `disposable`).
- `pg_restore` uses `--clean --if-exists --exit-on-error` (`backup.py` 214–221). That **drops existing objects** in the target. If `TRUST_CI_RESTORE_DATABASE_URL` is accidentally the production `trust_ci` database, a confirmed drill **will mutate live data**.
- Restore identity is whatever user is in the restore URL (typically a write role). The SELECT-only `trust_ci_backup` role cannot usefully restore.

## Related ops surface

- After restore: `psql` checks `to_regclass('public.trust_ci_jobs')` and `trust_ci_schema_migrations` (`backup.py` 225–244).
- Prune only deletes **verified** pairs older than retention and outside `keep_last`; tamper → fail closed, no deletes (`backup.py` 151–181).
- Tests assert systemd timer + `--confirm-disposable` in the script (`test_ops.py` 132–141), not DSN isolation.

## Implications for M0.2 drill on claw

- Create backups via the **systemd path** (or equivalent `--env TRUST_CI_DATABASE_URL=$TRUST_CI_BACKUP_DATABASE_URL`) so identity is `trust_ci_backup`.
- Point `TRUST_CI_RESTORE_DATABASE_URL` at a **separate disposable database**, not the compose `trust_ci` volume. Treat `--confirm-disposable` as “I already verified the DSN,” not as a safety interlock.
- Do not `compose down -v` as part of restore; that is a different, destructive path.
- Consider (out of this review’s write scope) rejecting restore when parsed restore `(host, port, dbname)` equals live `TRUST_CI_DATABASE_URL`.

## Verdict (pre-implementation)

Behavior matches the documented contract for confirm-gated drills. The live-DSN footgun remains: **wrong restore URL + `--confirm-disposable` = live wipe.** Drill runbooks must treat DSN construction as the real safety gate.
