# Rollback plan — Refresh workflow upstream versions and commits

## Trigger conditions

Parser/sample incompatibility, stale/incorrect release identity, or metadata mistakenly treated as install or authority input.

## Application rollback

Forward-fix the metadata and affected regression test through a successor PR. No runtime/parser behavior changes, deployment or data migration occurs in this change.

## Data recovery / forward-fix

No stored operational data is changed. Keep original upstream observation provenance; add a dated correction rather than claiming the old observation was current.

## Verification after rollback

Rerun the focused workflow tests, route verifier and independent reviews; require the App-owned check on the successor PR's exact head before merge.
