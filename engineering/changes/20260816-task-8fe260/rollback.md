# Rollback

```bash
gh release delete v2.0.8 --yes
git push origin :refs/tags/v2.0.8
git tag -d v2.0.8
```

Do not force-push main. Do not touch v2.0.7.
