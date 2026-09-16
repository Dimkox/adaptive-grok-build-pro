# Rollback plan — Release sync 2.0.16 to 2.0.17: identity bump R, artifact child A, tag release and successor SR per pinned doctrine

## Trigger conditions

- A coupled test literal was missed, so the identity surface disagrees (`VERSION` versus README/CHANGELOG/ROADMAP/`__version__`).
- A published fact (`v2.0.16` identifiers, released digests, milestone records) was accidentally rewritten instead of appended.
- The `v2.0.17` candidate is presented as published, tagged or activated anywhere in the tree.

## Application rollback

`R` creates nothing external: no tag, no release, no artifact bytes. Rollback is `git revert <R merge commit>` on a fresh pull request, which restores the `2.0.16` candidate wording and the closed `local_candidate` slot in one step, with the three coupled test modules moving back in the same commit.

If a content problem is narrower than the identity move, forward-fix in a follow-up pull request (maximum two steps) rather than reverting a published record.

## Data recovery / forward-fix

No migration, no database and no runtime state is involved; PostgreSQL migrations 001-018 stay frozen and untouched. If `A` is already merged but the tag was not created, the artifact bytes remain harmless in `main` and the sequence resumes forward from `A`'s merged commit — the bytes are never edited in place. If the tag or Release was published, it is immutable: recovery is a forward `v2.0.18` chain, not a deletion or a force-push.

## Verification after rollback

- `python3 -m unittest tests.test_structure tests.test_project_state tests.test_manifest_package` green in the rolled-back tree.
- `python3 scripts/grok_verify.py --mode pr` PASS.
- The exact-head `adaptive-trust-ci/verified@06ecf1c875bc` check SUCCESS on the rollback pull request before merging.
- `git tag --list 'v2.0.1*'` still ends at the last truly published release, proving no phantom tag was created.
