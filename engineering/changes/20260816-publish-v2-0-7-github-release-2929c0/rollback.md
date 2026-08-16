# Rollback

```bash
gh release delete v2.0.7 --yes
git push origin :refs/tags/v2.0.7
git tag -d v2.0.7
```

Do not touch v2.0.6 / v2.0.5. No force-push.
