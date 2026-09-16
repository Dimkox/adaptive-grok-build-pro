# Rollback plan — v2.0.17 successor

## Trigger conditions

The record disagrees with the immutable remote truth (tag target, digests, check run), or it over-claims an operational effect.

## Application rollback

`git revert` this commit: it restores the candidate wording and the v2.0.16 published record. Never delete or move `v2.0.17` — the published tag and Release are immutable, so a wrong record is fixed forward.

## Data recovery / forward-fix

No database, migration or runtime state is involved. A corrected record ships as a follow-up documentation pull request with the same lockstep rules.

## Verification after rollback

- `python3 -m unittest tests.test_structure tests.test_project_state tests.test_manifest_package` green in the rolled-back tree.
- `git tag --list 'v2.0.1*'` still ends at `v2.0.17`, proving the rollback moved no release.
- Exact-head App check SUCCESS on the rollback pull request before merging.
