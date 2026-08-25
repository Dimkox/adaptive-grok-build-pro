# Docs research — M0.2 backup / restore / restart drill

Change: `20260824-m0-2-backup-restore-restart-drill-on-claw-d5291e`  
Route: `d5291e6a1516`  
Scope: recover **documented** commands and report/plan rules. No invented flags. This slice does **not** complete M0.2 and does **not** register a GitHub webhook.

Invariant tests that docs/report must keep green (`trust-ci/tests/test_m0_invariants.py`):

- Activation report, spec, and plan must not contain PEM markers (`BEGIN RSA PRIVATE KEY`, `BEGIN OPENSSH PRIVATE KEY`).
- After the `Check Run id` header, the value cell must **not** contain `UNKNOWN`.
- Plan must still say **`local HMAC`**.
- Plan must still say **`no public HTTPS`** and/or **`not done`** (webhook).

---

## 1. Exact CLI and script invocations (required flags)

Source of truth for flags: `trust-ci/src/adaptive_trust_ci/cli.py`.  
`QUICKSTART.md` backup block is **incomplete** (omits `--database-label`, `--dump`, `--manifest`). Do not copy it as-is.

### `backup-create`

Required: `--database-label`.  
`--output-dir` optional; if omitted, `TRUST_CI_BACKUP_DIR` is required.

```bash
adaptive-trust-ci backup-create --database-label "$TRUST_CI_BACKUP_DATABASE_LABEL"
# or
adaptive-trust-ci backup-create --output-dir /path/to/backups --database-label adaptive-trust-ci-primary
```

Host systemd (`trust-ci/systemd/adaptive-trust-ci-backup.service`):

```bash
docker compose run --rm --no-deps \
  --env TRUST_CI_DATABASE_URL="$TRUST_CI_BACKUP_DATABASE_URL" \
  --volume "$TRUST_CI_BACKUP_DIR:/var/backups/adaptive-trust-ci" \
  api backup-create \
  --output-dir /var/backups/adaptive-trust-ci \
  --database-label "$TRUST_CI_BACKUP_DATABASE_LABEL"
```

Then prune (service `ExecStartPost`):

```bash
docker compose run --rm --no-deps \
  --volume "$TRUST_CI_BACKUP_DIR:/var/backups/adaptive-trust-ci" \
  api backup-prune \
  --directory /var/backups/adaptive-trust-ci \
  --keep-last "$TRUST_CI_BACKUP_KEEP_LAST" \
  --max-age-days "$TRUST_CI_BACKUP_MAX_AGE_DAYS"
```

`backup-prune`: `--directory` optional (else `TRUST_CI_BACKUP_DIR`); `--keep-last` default `14`; `--max-age-days` default `30`.

### `backup-verify`

Required: `--dump`, `--manifest`.

```bash
adaptive-trust-ci backup-verify --dump /path/to/file.dump --manifest /path/to/file.manifest.json
```

Compose wrapper used by `trust-ci/scripts/restore-drill.sh` (exactly two positional args; dump and manifest must share a directory; env `TRUST_CI_RESTORE_DATABASE_URL` required):

```bash
./trust-ci/scripts/restore-drill.sh <backup.dump> <backup.manifest.json>
```

That script runs:

```bash
docker compose -f trust-ci/compose.yaml run --rm --no-deps \
  --volume "$backup_dir:/restore:ro" \
  api backup-verify --dump "/restore/$dump_name" --manifest "/restore/$manifest_name"

docker compose -f trust-ci/compose.yaml run --rm --no-deps \
  --env TRUST_CI_RESTORE_DATABASE_URL="$TRUST_CI_RESTORE_DATABASE_URL" \
  --volume "$backup_dir:/restore:ro" \
  api restore-drill \
  --dump "/restore/$dump_name" \
  --manifest "/restore/$manifest_name" \
  --confirm-disposable
```

### `restore-drill`

Required args: `--dump`, `--manifest`.  
Required flag: `--confirm-disposable` (`backup.py` raises without it).  
Required env: `TRUST_CI_RESTORE_DATABASE_URL` (CLI `SystemExit` if empty). Target is disposable only.

```bash
TRUST_CI_RESTORE_DATABASE_URL='postgresql://…' \
  adaptive-trust-ci restore-drill \
  --dump /path/to/file.dump \
  --manifest /path/to/file.manifest.json \
  --confirm-disposable
```

Do **not** restore into the live `trust_ci` database. Do not paste URLs/secrets into the activation report.

### PostgreSQL restart drill (durable volume, not tmpfs)

Documented in `QUICKSTART.md` (from repo root):

```bash
./trust-ci/scripts/postgres-restart-drill.sh
```

Script (`trust-ci/scripts/postgres-restart-drill.sh`) uses `trust-ci/compose.test.yaml`, project `adaptive-trust-ci-pgrestart-${USER:-ci}-$$`, then:

- `docker compose … up -d --wait postgres-test`
- `docker compose … run --rm postgres-integration python3 -m tests.postgres_restart_probe seed`
- `docker compose … restart postgres-test`
- `docker compose … up -d --wait postgres-test`
- `docker compose … run --rm postgres-integration python3 -m tests.postgres_restart_probe verify`

Prints `postgres restart drill: PASS`. Cleanup: `down --volumes --remove-orphans`.

This is the **test** Postgres volume (`trust-ci-pgtest-data`), not a production dump of `claw` `trust-ci-postgres`.

### Alternate dump in rollout (not the CLI)

`engineering/runbooks/trust-ci-rollout.md` still shows raw:

```bash
docker compose exec -T postgres \
  pg_dump --format=custom --no-owner --file=/tmp/trust-ci.dump "$POSTGRES_DB"
docker compose cp postgres:/tmp/trust-ci.dump ./runtime/trust-ci.dump
```

That path has **no** SHA-256 manifest and is not what `backup-verify` / `restore-drill` consume. Prefer CLI `backup-create` + manifest pair for this drill.

### Kill switch (already dated pass; not this slice’s checkbox)

```bash
adaptive-trust-ci kill-switch on
adaptive-trust-ci kill-switch status
adaptive-trust-ci kill-switch off
```

(`rollout.md` documents `on` only.)

---

## 2. Activation report field `Backup/restore/restart drill`

File: `engineering/runbooks/trust-ci-activation-report.md`. Current cell: `UNKNOWN`.

**If the drill actually passes on `claw` (dated, no secrets):** write a one-line pass, same pattern as Kill switch, e.g. dated pass naming:

- `backup-create --database-label …` (label only, no URL)
- `backup-verify` + `restore-drill --confirm-disposable` against a **disposable** DB
- `./trust-ci/scripts/postgres-restart-drill.sh` PASS (or equivalent host restart proof)

**Keep `UNKNOWN`** if any of: dump without verified manifest, restore without `--confirm-disposable`, restore against live DB, restart drill not run, or secrets would be required to describe it.

Never paste PEM, JWT, webhook secret, admin token, DSN, or human keys (header of the report + `test_m0_invariants`).

Leave webhook, `main` protected, leftover Actions, bootstrap-exception as they are (`not done` / `UNKNOWN` as today). Do not claim M0.2 complete.

---

## 3. Plan checkbox split

Plan file: `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` M0.2 item:

> Source-mutation fail-closed; backup/restore/restart. …

That is **one** checkbox covering two proofs. **Split:**

- Check **only** backup/restore/restart if this drill passes (and keep kill-switch dated pass).
- Leave **source-mutation fail-closed** unchecked: jobs are still `needs_approval` / `action_required`; tracked-source mutation fixture (`rollout.md` step 10) is not this slice.

Webhook line stays **not done** (`no public HTTPS`). Disposable PR line stays **partial** + **`local HMAC`**. Do not mark M0.2 complete.

---

## 4. SHA / Check Run id cells vs infinite-SHA

Committed report (current):

| Field | Committed |
| --- | --- |
| Disposable PR head SHA | `1fc942065a124ce75659bd082519d8ebc37774e8` |
| Check Run id | `97390635614` |

Live SHA-change already proven (operator context, not this researcher’s observation of GitHub): head `ce03c87…` / Check Run `97406973020`.

`test_m0_invariants.test_activation_report_operator_safe` only forbids `UNKNOWN` in the **Check Run id** value cell. It does not pin a specific SHA.

**Recommendation for this slice:**

- **Do not** blank the Check Run id (`UNKNOWN` fails the test).
- **Do not** silently replace history with an endless latest SHA on every later commit (infinite-SHA).
- **Do** keep first-proof history (`1fc9420` / `97390635614`, local HMAC, `needs_approval`) in plan and/or a history note.
- **Do** update the report’s **current** PR head SHA and Check Run id to the live SHA-change pair (`ce03c87…` / `97406973020`) **if** those ids are already operator-confirmed, so the filled cells match live authority without claiming webhook or M0.2 done.

If this slice’s implementer cannot independently confirm `ce03c87` / `97406973020`, leave the committed `1fc9420` / `97390635614` pair (still not `UNKNOWN`) and record the newer ids only in change-package evidence — not invented.

---

## 5. Explicit non-claims

- GitHub-registered webhook: **not done** (plan + report: loopback HMAC, no public HTTPS).
- M0.2: **not complete** (webhook, SHA-change plan checkbox, human Ed25519 requeue, source-mutation, `main` unprotected).
- Do not run `branch-protect`.
- Do not read `.env` or PEM.

## Sources

- `trust-ci/src/adaptive_trust_ci/cli.py`
- `trust-ci/src/adaptive_trust_ci/backup.py`
- `trust-ci/scripts/restore-drill.sh`
- `trust-ci/scripts/postgres-restart-drill.sh`
- `trust-ci/systemd/adaptive-trust-ci-backup.service`
- `trust-ci/env/backup.env.example`
- `trust-ci/README.md` (backup classes; no extra CLI flags)
- `QUICKSTART.md` (restart script; incomplete backup CLI)
- `engineering/runbooks/trust-ci-rollout.md` (raw `pg_dump`; restart as acceptance; kill-switch)
- `engineering/runbooks/trust-ci-activation-report.md`
- `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md`
- `trust-ci/tests/test_m0_invariants.py`
- `trust-ci/tests/test_ops.py`
