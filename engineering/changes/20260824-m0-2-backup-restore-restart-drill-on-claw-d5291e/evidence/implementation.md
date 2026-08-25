# Implementation — M0.2 backup restore restart drill

Write owner: `general_implementer`. No push. Live volume never a restore TARGET.

## Drill

- Dump identity: `trust_ci_backup`; label `adaptive-trust-ci-primary`
- `size_bytes`: 26496; sha256 prefix `c46da2cb9754`
- `backup-verify`: `verified`
- Restore: throwaway tmpfs Postgres, dbname `trust_ci_restore`, network `adaptive-trust-ci_trust-ci`; mounts excluded `adaptive-trust-ci_trust-ci-postgres`; then `docker rm -f` throwaway only
- Restore JSON: `status=restored-and-verified`
- Jobs before/after `compose --project-name adaptive-trust-ci restart postgres`: 2 / 2
- GET `http://127.0.0.1:18080/health/ready`: 200
- Tracked `trust-ci/compose.yaml` unchanged

Client/server version: live API image ships PostgreSQL 15 clients; catalog is 17.6. Dump/restore clients matched 17 on postgres/throwaway only.

## Docs

- Activation report backup cell: 2026-08-24 pass (CLI names, no DSN). Check Run id remains `97390635614`. History notes `97406973020` / `ce03c87`.
- Plan: backup/restore/restart checked; source-mutation open; SHA-change proven vs policy retitle still open. Not M0.2 complete.
- `decisions.md`: live volume source+restart only.
- `test_m0_invariants.py`: backup cell dated pass; no PEM; Check Run id not UNKNOWN; local HMAC; no public HTTPS / not done.

## Out of scope still

Public webhook, human Ed25519, policy/holdout retitle, protect `main`, git push.
