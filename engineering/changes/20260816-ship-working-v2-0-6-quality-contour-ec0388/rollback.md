# Rollback

If 2.0.6 is not published: revert the ship commit. Leave tag `v2.0.5` and Release `v2.0.5` untouched.

If a later human publishes 2.0.6 and it must be withdrawn:

```bash
gh release delete v2.0.6 --yes
git push origin :refs/tags/v2.0.6
git tag -d v2.0.6
```

No force-push of `main`.
