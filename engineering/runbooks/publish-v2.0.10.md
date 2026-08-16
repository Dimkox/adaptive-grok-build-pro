# Publish v2.0.10

Last mile is GitHub CLI, not GitHub Actions.

```bash
python3 scripts/package_stack.py
cp dist/adaptive-grok-build-pro-v2.0.10.zip* packages/
git tag -a v2.0.10 -m "v2.0.10"
git push origin main
git push origin v2.0.10
gh release create v2.0.10 packages/adaptive-grok-build-pro-v2.0.10.zip packages/adaptive-grok-build-pro-v2.0.10.zip.sha256 --title "Adaptive Grok Build Pro v2.0.10" --notes-file dist/RELEASE-NOTES.md
```

Rollback:

```bash
gh release delete v2.0.10 --yes
git push origin :refs/tags/v2.0.10
git tag -d v2.0.10
```
