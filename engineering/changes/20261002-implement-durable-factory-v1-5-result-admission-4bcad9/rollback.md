# Rollback plan — Implement durable Factory v1.5 result admission persistence

## Trigger conditions

Incorrect tenant visibility, weakened validation, non-atomic writes, outbox insertion, or unbounded lock waits.

## Application rollback

Disable the admission endpoints or return the prior explicit 503 seam; do not delete immutable evidence rows.

## Data recovery / forward-fix

Ship one additive corrective migration. Migration 024 is non-destructive and performs no backfill.

## Verification after rollback

POST/GET fail closed, existing V1 behavior remains green, runtime has no table DML, and outbox count is zero.
