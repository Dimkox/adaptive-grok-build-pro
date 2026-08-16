# Rollback

```bash
gh release delete v2.0.10 --yes
git push origin :refs/tags/v2.0.10
git tag -d v2.0.10
```

Do not force-push. Do not delete v2.0.9. Latest falls back to v2.0.9.
