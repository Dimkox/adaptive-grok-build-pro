# Rollback plan — Consolidate milestone branch state and delivery

## Trigger conditions

Rollback or forward-fix if schema version 2 breaks a repository consumer, current handoff files disagree, a milestone is falsely marked delivered, continuation work is omitted, or the graph ceases to be exact K16.

## Application rollback

Before merge, abandon only this isolated source branch/PR when explicitly authorized. After merge, prefer a protected forward-fix PR with newly observed facts; if consumer breakage requires reversal, revert the state-repair merge through another protected PR. Never rewrite `main` or delete evidence branches as rollback.

## Data recovery / forward-fix

No operational data changes. Recover by fetching current refs, re-observing GitHub/Trust CI read-only state, correcting the JSON/docs/inventory together, and preserving all historical analysis. A documentation revert cannot undo a product or Trust CI delivery.

## Verification after rollback

Parse `PROJECT_STATE.json`, rerun state/epoch/inventory/graph tests and `git diff --check`, verify README/START_HERE agreement, and require a fresh exact-head App check for the recovery PR.
