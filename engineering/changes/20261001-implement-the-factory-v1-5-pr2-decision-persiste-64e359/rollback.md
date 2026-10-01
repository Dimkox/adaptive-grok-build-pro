# Rollback plan — Implement the Factory v1.5 PR2 decision persistence contour on current main: transplant the five existing decision persistence commits from the isolated branch, resolve bounded API and data persistence conflicts, preserve behavior and tests, and deliver the isolated candidate

## Trigger conditions

Migration/readiness failure, digest drift, replay regression, partial transaction, or restart loss.

## Application rollback

Before migration application, revert the candidate. After schema 23 exists, retain schema-23-capable code and stop supplying the optional decision record while preparing a forward fix; do not run a schema-22 binary against DB 23.

The 800000-byte Factory-test budget and the dependent PR2 test contour roll back
together. Reverting only the policy is invalid because the unchanged governed
contour deterministically exceeds the previous 775000-byte bound.

## Data recovery / forward-fix

Migration 023 is append-only and has no destructive backfill. Never down-migrate or edit it. If old-binary rollback is mandatory, restore a separate schema-22-compatible database.

## Verification after rollback

Readiness reports the expected schema, legacy transitions work without a decision, and existing decision rows/digests/cardinality remain unchanged.
