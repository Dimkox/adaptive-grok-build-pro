# Requirements

## Acceptance

- [ ] `backup-create --database-label adaptive-trust-ci-primary` writes dump+manifest under gitignored `trust-ci/runtime/backups/`; print only dump_path, manifest_path, sha256, size_bytes (size > 0).
- [ ] `backup-verify` reports verified on that pair.
- [ ] `restore-drill --confirm-disposable` restores into throwaway DSN whose host is not `postgres` / live postgres container / loopback and dbname is not `trust_ci`. Throwaway mounts do not include `adaptive-trust-ci_trust-ci-postgres`. Then `docker rm -f` throwaway only.
- [ ] Job `count(*)` from live postgres before restart equals after `docker compose -p adaptive-trust-ci restart postgres`. `/health/ready` 200. Volume still exists.
- [ ] Activation report `Backup/restore/restart drill` is a dated pass without DSN/PEM. Plan: only backup/restore/restart half checked; source-mutation still open. `local HMAC` and webhook not done remain.
- [ ] `python3 -m unittest trust-ci.tests.test_m0_invariants` and `python3 scripts/grok_verify.py --mode pr` after last product write.
- [ ] No `git push`. Leftovers 9d97f8/37bf04/33e0c2 unstaged.

## Failure stops

- Restore URL looks live → abort, do not confirm.
- `/health/ready` not 200 after restart → stop; no down -v.
- Secret printed → stop.
