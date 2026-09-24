# Rollback plan — Fix issue #73: rename current evidence fingerprint fields that trigger GitGuardian secret heuristics while preserving historical evidence immutability and schema/test compatibility.

## Trigger conditions

Any approved rename that breaks a closed reader/schema or touches historical evidence is a
rollback trigger.

## Application rollback

Forward-fix the current producer/reader pair or restore new writes to `tree_fingerprint` while
retaining dual-name read support. Never rewrite immutable history or existing runtime grant files
as rollback.

## Data recovery / forward-fix

## Verification after rollback

Run compatibility tests and compare historical artifact bytes; external GitGuardian status remains
an out-of-band check.
