# Rollback

```bash
gh release delete v2.0.6 --yes
git push origin :refs/tags/v2.0.6
git tag -d v2.0.6
```

Restore workflow only by reverting the ban commit. Do not force-push. Leave v2.0.5.
