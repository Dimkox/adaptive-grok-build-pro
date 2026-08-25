# Architecture

Authority: `evidence/analysis-architect.md` and `evidence/analysis-code_reviewer.md`.

Live postgres volume `adaptive-trust-ci_trust-ci-postgres` is never a restore destination. Dump uses role `trust_ci_backup` via compose `run --rm --no-deps api` with `TRUST_CI_DATABASE_URL` overridden from backup env in a `/tmp` helper (`set +x`, never print). Restore uses throwaway tmpfs Postgres on `adaptive-trust-ci_trust-ci`. Restart is `compose restart postgres` only.

Tracked `trust-ci/compose.yaml` and host overlay stay unchanged.

## Grants

Mint `external-write` for compose/docker run/exec/restart on this fingerprint if hooks require it. Resource exact (compose project `adaptive-trust-ci` / docker throwaway name), not `*`. No git-push-branch.
