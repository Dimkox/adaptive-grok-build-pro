# Rollback plan — Fix PROJECT_STATE 2.1.0 release candidate identity so the new source-only candidate has no artifact hashes while preserving the immutable 2.0.19 artifact record

## Trigger conditions

Any regression that conflates the published release with the source candidate.

## Application rollback

Forward-fix the state record; do not alter the published v2.0.19 release.

## Data recovery / forward-fix

Restore the two separate identities from authoritative release evidence and local source state.

## Verification after rollback

Rerun project-state, manifest, and structure lockstep tests.
