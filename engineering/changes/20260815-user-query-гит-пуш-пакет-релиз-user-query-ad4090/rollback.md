# Rollback

```bash
gh release delete v2.0.5 --yes
git push origin :refs/tags/v2.0.5
git tag -d v2.0.5
```

If `main` must revert: revert the 2.0.5 commit(s) and push. Remove unpublished `packages/adaptive-grok-build-pro-v2.0.5.zip*`.
