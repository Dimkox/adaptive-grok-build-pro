# M0.2 backup restore restart drill on claw

Change ID: `20260824-m0-2-backup-restore-restart-drill-on-claw-d5291e`
Route: `d5291e6a1516`
Write owner: `general_implementer`

## Problem

User «далее» after SHA-change. Remaining M0.2: public HTTPS webhook, human Ed25519, policy/holdout retitle, backup/restore. Only backup/restore/restart can run on claw this turn.

## Outcome

Live `/health/ready` 200 after: backup-create dump+manifest; backup-verify; restore-drill `--confirm-disposable` into a throwaway DB (never live volume); `compose restart postgres` without `-v` keeps catalog. Activation report drill cell is a dated pass. Not M0.2 complete.

## Scope

### In scope

- backup-create as `trust_ci_backup` into gitignored `trust-ci/runtime/backups/`
- restore-drill into tmpfs throwaway Postgres on network `adaptive-trust-ci_trust-ci`, hostname ≠ `postgres`, dbname ≠ `trust_ci`
- live `docker compose -p adaptive-trust-ci restart postgres` (no down, no `-v`)
- Fill activation-report backup field; split plan checkbox; characterization in `test_m0_invariants` if the cell is a dated pass
- Commit leftover beee95 evidence + this package

### Out of scope

- `git-push-branch` (this «далее» is the drill, not a new push)
- Public webhook, human keys, policy retitle, PEM, protect `main`, merge
- Live restore, `compose down -v` on `adaptive-trust-ci`
- Tracked compose.yaml / overlay edits
- Leftover `9d97f8` / `37bf04` / `33e0c2`

## Controller rulings

- Live catalog is backup SOURCE and restart subject, never restore TARGET.
- No push this slice. Origin stays `ce03c87`.
- Report: Check Run id cell stays numeric. Keep first proof `97390635614`/`1fc9420` as history; current PR head `ce03c87`/`97406973020` may be noted in prose or extra rows. Do not claim webhook done.
