# Rollback plan — M9 staged delivery on exact M8 f53275d

## Trigger conditions

Rollback or forward-fix if M9 duplicates M8 authority, permits caller eligibility/currentness, skips a stage, reaches production, applies a duplicate fake effect, accepts a stale/reordered chain, or selects recovery that increases authority.

## Application rollback

Before publication, revert the add-only M9 package, tests, architecture, and handoff documentation. Exact M8 `f53275d5ed84022200419b399c799a995ed91a45` remains the intact predecessor.

## Data recovery / forward-fix

No migration, persistent state, operational effect, or backfill exists. The fake adapter is process-local; discard its in-memory state. Contract defects require a bounded pre-publication forward-fix or a new version.

## Verification after rollback

Confirm the M9 package and architecture node are absent, M4-M8 product paths and migrations `001`-`018` match the exact predecessor, and the M8 tree fingerprint is restored.
