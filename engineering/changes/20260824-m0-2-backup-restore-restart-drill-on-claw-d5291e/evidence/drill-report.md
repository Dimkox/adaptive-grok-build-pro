# M0.2 backup / restore / restart drill (claw, 2026-08-24)

Operator-safe. No DSN, PEM, JWT, webhook secret, or dump bytes.

| Signal | Result |
| --- | --- |
| Dump | `backup-create` identity `trust_ci_backup`; `--database-label adaptive-trust-ci-primary` |
| size_bytes | 26496 (> 0) |
| sha256 prefix | `c46da2cb9754` |
| backup-verify | `status=verified`; same digest and size |
| Restore | throwaway tmpfs Postgres `adaptive-trust-ci-restore-throwaway-*` on network `adaptive-trust-ci_trust-ci`; dbname `trust_ci_restore`; mounts did not include `adaptive-trust-ci_trust-ci-postgres`; host was not `postgres` / live container / loopback |
| restore status | `restored-and-verified` |
| Throwaway | `docker rm -f` throwaway only; live project not `down` |
| Jobs before restart | 2 |
| Restart | `docker compose --project-name adaptive-trust-ci restart postgres` (no `-v`) |
| Jobs after | 2 (equal) |
| GET `/health/ready` | 200 |
| Volume | `adaptive-trust-ci_trust-ci-postgres` still present |
| Tracked compose | `git diff --exit-code -- trust-ci/compose.yaml` |

Live catalog was backup SOURCE and restart subject only. Not M0.2 complete.

Note: live `api` image `pg_dump`/`pg_restore` are PostgreSQL 15; catalog is 17.6. Dump used matching 17 client as role `trust_ci_backup`. Restore used matching 17 client on the throwaway only.
