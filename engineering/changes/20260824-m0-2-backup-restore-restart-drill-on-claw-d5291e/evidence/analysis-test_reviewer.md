# Test review (pre-implementation) — M0.2 backup / restore / restart drill on claw

Change: `20260824-m0-2-backup-restore-restart-drill-on-claw-d5291e`  
Route: `d5291e6a1516`  
Agent: `test_reviewer` (read-only)  
Tree: product tests inspected; no `.env` / PEM / credentials read.

## Verdict

Unit and characterization coverage for **library** backup/restore and **script/compose** restart is already strong. **Live claw drill** against the production named volume (`trust-ci-postgres`) and filling the activation-report cell is **not** covered by any automated test. That live path is the work of this slice.

Do not treat `python3 -m unittest trust-ci.tests.test_backup` or `test_ops` as proof that claw survived backup/restore/restart.

---

## What already covers backup-create, backup-verify, restore-drill `--confirm-disposable`

### Library (mocked `pg_dump` / `pg_restore` / `psql`) — `trust-ci/tests/test_backup.py`

| Test | Behavior |
| --- | --- |
| `test_create_backup_writes_atomic_dump_and_canonical_manifest` | `create_backup` + `verify_backup` status `verified`; custom format; `0600`; credentials via `PGSERVICEFILE` not argv |
| `test_verify_backup_rejects_tampering` | digest mismatch |
| `test_restore_requires_explicit_disposable_confirmation` | `restore_drill(..., confirm_disposable=False)` raises `BackupError` matching `confirm-disposable` |
| `test_restore_verifies_before_pg_restore_and_runs_in_fail_closed_mode` | `confirm_disposable=True`; `pg_restore --clean --if-exists --exit-on-error`; `psql ON_ERROR_STOP=1`; URL not on argv |
| `test_failed_pg_dump_leaves_no_partial_backup` | fail-closed empty dir |
| Retention tests | prune verified pairs; fail-closed on tamper |

These exercise `adaptive_trust_ci.backup`, not live Postgres and not the CLI process.

### CLI wiring

`trust-ci/src/adaptive_trust_ci/cli.py` registers `backup-create`, `backup-verify`, `restore-drill` and `--confirm-disposable`. **No** `test_cli*.py`. Parser/dispatch is untested except indirectly via systemd/script string checks.

### Operator script + systemd — `trust-ci/tests/test_ops.py` `test_backup_timer_and_restore_drill_are_explicit`

- `trust-ci/systemd/adaptive-trust-ci-backup.service` contains `backup-create` and `TRUST_CI_BACKUP_DIR`
- timer `Persistent=true` / `OnCalendar=`
- `trust-ci/scripts/restore-drill.sh` contains `--confirm-disposable` and `backup-verify` (and, in source, `api restore-drill`)

This is **static text**. It does not run compose, dump, or restore.

`trust-ci/scripts/smoke.sh` only asserts `restore-drill.sh` **exists**.

---

## What already covers postgres restart recovery (named volume)

`trust-ci/tests/test_ops.py` `test_postgres_restart_drill_uses_named_volume_and_container_restart`:

- `trust-ci/compose.test.yaml` mounts `trust-ci-pgtest-data:/var/lib/postgresql/data`, no `tmpfs:`
- `trust-ci/scripts/postgres-restart-drill.sh` contains `compose restart postgres-test` and `postgres_restart_probe seed|verify`

`trust-ci/tests/postgres_restart_probe.py` is the seed/verify probe (durable job survives restart). It is **not** invoked by unittest; only by the bash drill against **compose.test**, project `adaptive-trust-ci-pgrestart-*`, with `down --volumes` on EXIT.

Production `trust-ci/compose.yaml` uses `trust-ci-postgres:/var/lib/postgresql/data`. **No test** asserts that **that** volume survives `compose restart postgres` on claw.

---

## Live drill that is NOT covered

Activation report cell:

`Backup/restore/restart drill | UNKNOWN`

Kill-switch already has a dated pass; backup/restore/restart does not.

**Not covered (this slice’s live work):**

1. On **claw**, `adaptive-trust-ci backup-create` against the **live** compose Postgres (`trust-ci-postgres` named volume), then `backup-verify` on that dump+manifest.
2. `restore-drill --confirm-disposable` into an **explicitly disposable** database (`TRUST_CI_RESTORE_DATABASE_URL`), **not** overwriting primary `trust_ci` without the flag.
3. **Production** compose restart of `postgres` (or equivalent) and proof durable jobs/leases still exist after the named volume comes back — `postgres-restart-drill.sh` is the **test** stack only.
4. Filling the activation-report cell with a dated, operator-safe pass (no PEM, no DSN, no dump bytes).

Also still open for M0.2 generally (out of this drill’s unit tests): public HTTPS webhook, SHA-change invalidation, human Ed25519 requeue. Do not fold those into backup tests.

---

## Characterization to add in `test_m0_invariants` if the report field becomes a dated pass

Keep existing invariants: no PEM markers; Check Run id cell not `UNKNOWN`; plan still has `local HMAC` and webhook `not done` / `no public HTTPS`.

**Add one focused assertion** on `engineering/runbooks/trust-ci-activation-report.md`, analogous to kill-switch language, for example:

- Split on the `Backup/restore/restart drill` row (or equivalent header) and require the value cell to contain a **date** (`2026-`) and **`pass`**.
- Optionally require operator-safe tokens such as `backup-create`, `backup-verify`, `restore-drill`, `--confirm-disposable`, and/or named volume `trust-ci-postgres` **if** the report actually records those words.
- **Must not** require secrets: no assertion on DSN, `TRUST_CI_RESTORE_DATABASE_URL` values, dump paths under host backup dirs, PEM, JWT, webhook secret, or dump SHA of live data.
- **Must not** assert `main` is unprotected (`main protected | false`). Plan: “Do not assert main is unprotected (that would fight M0.3).” Current `test_m0_invariants` already omits that row; keep it that way.

Do **not** parse Check Run SHA as a proxy for this drill. Do **not** require the M0.2 plan checkbox for backup/restore/restart to be `[x]` if other M0.2 items remain open — scope the test to the **report field**, matching how kill-switch was dated in-report while the plan line still lists remaining M0.2 gaps.

If the report stays `UNKNOWN` this slice, **do not** add a “must be pass” assertion or CI will fail. Either land the dated pass and the characterization together, or keep tests frozen until the host drill is written into the report.

---

## Suggested automated vs live split

| Layer | Command / evidence | Already tested? |
| --- | --- | --- |
| Unit | `create_backup` / `verify_backup` / `restore_drill` | Yes — `test_backup.py` |
| Static | systemd `backup-create`; `restore-drill.sh` flags | Yes — `test_ops.py` |
| Isolated compose | named test volume + `postgres-restart-drill.sh` | Script+probe exist; unittest is static only |
| Live claw | backup-create → verify → restore-drill --confirm-disposable; production postgres named-volume restart | **No** — operator + report cell |
| Invariants | dated pass in activation report | **Add after** the report is filled |

Preflight after implementation: `python3 -m unittest trust-ci.tests.test_backup trust-ci.tests.test_ops trust-ci.tests.test_m0_invariants` then `python3 scripts/grok_verify.py --mode pr`. That still does not replace the live claw drill receipt.
