# Rollback plan — M0 consolidate git and continue live authority proof

## Trigger conditions

- Kill-switch stuck on
- `/health/ready` not 200
- Accidental staging of leftover packages or secrets

## Application rollback

- `adaptive-trust-ci kill-switch off` (or unlink host `runtime/control/STOP` via compose mount). Leave postgres+api+worker.
- Unpushed commit: `git restore --staged` / `git reset` on this branch only. No force-push.
- Never PATCH Check Run `97390635614` to success. Never `compose down -v`.

## Data recovery / forward-fix

No catalog mutation intended. Kill-switch is a file, not SQL.

## Verification after rollback

`GET http://127.0.0.1:18080/health/ready` returns 200. Metric `adaptive_trust_ci_kill_switch 0` if scraped. `main` still unprotected.
