# Rollback

```bash
gh release delete v2.0.6 --yes
git push origin :refs/tags/v2.0.6
git tag -d v2.0.6
```

Do not touch v2.0.5. No force-push.
