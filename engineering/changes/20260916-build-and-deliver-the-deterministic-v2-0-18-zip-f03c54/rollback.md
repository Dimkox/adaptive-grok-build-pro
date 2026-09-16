# Rollback plan — v2.0.18 artifact child

## Trigger conditions

- The two builds disagree, so the shipped bytes are not reproducible.
- The recorded `source_parent` is not the commit whose tree was packed.
- Any publication field was set early (`published`, `external_effect`, `operational_activation`, a non-null self-recorded `merge_commit`).

## Application rollback

`git revert` the merge commit of this pull request: it removes two tracked files and a record flip, touches no runtime and no published release. If the tag or Release already exists, the artifact is immutable: fix forward with `v2.0.18` rather than moving or deleting `v2.0.18`.

## Data recovery / forward-fix

No migration and no host state; PostgreSQL 001-018 untouched. Rebuild from a fresh exact-SHA clone instead of editing bytes in place.

## Verification after rollback

- `python3 -m unittest tests.test_structure tests.test_project_state tests.test_manifest_package` green.
- `git ls-files packages/ | grep -c 2.0.18` back to zero and `git tag --list 'v2.0.1*'` ending at the last real release.
- `grok_verify --mode pr` plus the exact-head App check SUCCESS on the rollback pull request.
