# Rollback plan — Factory Linux installer from Liqvera prototype

## Trigger conditions

Integrity/preflight/health failure, interrupted switch, incompatible data schema, or state/pointer mismatch.

## Application rollback

Stop the candidate, retain evidence, and keep or restore the prior pointer only when its schema compatibility is proven. Otherwise require verified backup restore and report blocked.

## Data recovery / forward-fix

Never run down migrations. Preserve volumes/config/backups and reconcile durable operation state before another attempt.

## Verification after rollback

Prior exact identity is active and healthy; candidate is inactive; data/config remain; operation state records the observed outcome.
