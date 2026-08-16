# Rollback

Deletes only the new advertisement. Does not touch `v2.0.4` or rewrite `main`.

```bash
gh release delete v2.0.5 --yes
git push origin :refs/tags/v2.0.5
git tag -d v2.0.5
```

Do not force-push. Do not delete `packages/adaptive-grok-build-pro-v2.0.5.zip*`. Revert of `7c0ae75` is a separate decision.
