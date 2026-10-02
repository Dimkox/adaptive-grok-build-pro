# Rollback plan — Add Factory v1.5 decision accounting boundary behavior from source commit 531089f to the PR2 persistence foundation: enforce bounded cost and duration values and exact persisted accounting invariants as a new feature slice, with regression tests and isolated PR delivery

## Trigger conditions

Valid in-range summaries regress or both discovery paths no longer execute the shared cases.

## Application rollback

Forward-fix the bounded guard/test adaptation; no database rollback is required.

## Data recovery / forward-fix

No data is written by this helper and no migration is introduced. Retain PR2 schema-23 decision history.

## Verification after rollback

Run both focused discovery modules and the full PR verifier on the corrected tree.
