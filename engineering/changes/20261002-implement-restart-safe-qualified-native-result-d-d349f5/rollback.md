# Rollback plan — Implement restart-safe qualified native result dispatch

## Trigger conditions

Unexpected pre-upgrade rows, unsafe role topology, identity mismatch or ambiguous state regression.

## Application rollback

Keep the dispatcher disabled and roll back Python entrypoints. Do not reverse migration 025 in place.

## Data recovery / forward-fix

Forward-fix schema/functions. Preserve unknown/blocked rows and reconcile by deterministic GET;
never delete or blind-repost them.

## Verification after rollback

Assert dispatcher disabled, no new outbox rows, admission still reports outbox_created=false and
all qualification channels remain unavailable.
