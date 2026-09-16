# Rollback — release-chain convention and inspected causes

## Trigger conditions

A quoted cause turns out not to match the retained record, or the convention sentence conflicts with a later schema decision.

## Application rollback

`git revert` the merge commit of this pull request; it restores the previous prose and the three placeholder strings. No data, tag, artifact or runtime state is involved.

## Data recovery / forward-fix

Not applicable; at most one forward documentation step.

## Verification after rollback

- `python3 -m unittest tests.test_project_state tests.test_structure` green.
- The exact-head App check SUCCESS on the rollback pull request before merging.
