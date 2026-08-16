# Rollback

If the 2.0.8 commit is on origin/main and must come off: do **not** force-push. Ship a forward fix as 2.0.9.

If the commit is local only: `git reset --keep origin/main` on a clean confirmation. Restore 2.0.7 pins. Leave `v2.0.7` and its zip untouched.

```bash
# only if a later tag/release was created
gh release delete v2.0.8 --yes
git push origin :refs/tags/v2.0.8
git tag -d v2.0.8
```
