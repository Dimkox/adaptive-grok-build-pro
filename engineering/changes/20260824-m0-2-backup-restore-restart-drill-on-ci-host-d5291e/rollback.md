# Rollback

- Throwaway: `docker rm -f` that container only.
- Live: never `compose down -v`. If restart leaves API 503, wait for postgres healthy; do not flip kill-switch unless it was left on.
- Unpushed commit: `git reset` on this branch only.
- Dumps in `trust-ci/runtime/backups/` may stay gitignored or be deleted; they are not the live catalog.
