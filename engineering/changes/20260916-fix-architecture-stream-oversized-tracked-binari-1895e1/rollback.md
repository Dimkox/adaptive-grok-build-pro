# Rollback — stream oversized tracked binaries

## Trigger conditions
Evidence that a streamed profile disagrees with the buffered implementation for a file at or below the limit, or that a tampered oversized object can pass where the pre-fix code refused.

## Application rollback

`git revert` this single commit: analysis returns to failing on oversized tracked files, which is the known issue #80 red, not a loss of data or state. No migration, no runtime artefact and no external effect is involved.

## Data recovery / forward-fix
None needed; maximum one forward step, and it must restore streaming rather than widen the memory limits.

## Verification after rollback
- `python3 -m unittest tests.test_architecture_fitness` green with the new tests removed or adjusted in the same revert.
- `python3 scripts/grok_verify.py --mode pr` plus the exact-head App check on the rollback pull request.
