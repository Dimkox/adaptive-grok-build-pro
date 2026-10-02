# Rollback plan — Publish unverified transport branch for the assembled 2.1.0 release candidate; no merge tag or release

## Trigger conditions

Verifier/review failure, migration identity drift, contract incompatibility, misleading release claims, or external exact-head check failure.

## Application rollback

Before merge, close the PR or push a forward-fix commit. After any later merge, keep optional paths disabled and use a separately reviewed forward-fix; do not rewrite migration history.

## Data recovery / forward-fix

Preserve result/outbox rows and all dirty worktrees. Prefer disabling dispatch and repairing additively; never drop or renumber shipped migrations.

## Verification after rollback

Run the full PR verifier and exact migration/restart tests on the repaired head, repeat independent reviews, and require a fresh external exact-head Trust CI check.
