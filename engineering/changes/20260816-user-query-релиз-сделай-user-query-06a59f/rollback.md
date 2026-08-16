# Rollback

```bash
gh release delete v2.0.9 --yes
git push origin :refs/tags/v2.0.9
git tag -d v2.0.9
```

Do not force-push. Do not delete v2.0.8.
