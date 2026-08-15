# Publish v2.0.5

User-authorized publish. Rollback if the tag or GitHub Release must be withdrawn.

Agents must not run `git push`, `git tag`, or `gh release`; humans own those commands.

## Commands

```bash
python3 scripts/package_stack.py
cp dist/adaptive-grok-build-pro-v2.0.5.zip* packages/
git tag -a v2.0.5 -m "v2.0.5"
git push origin main
git push origin v2.0.5
gh release create v2.0.5 packages/adaptive-grok-build-pro-v2.0.5.zip packages/adaptive-grok-build-pro-v2.0.5.zip.sha256 --notes-file dist/RELEASE-NOTES.md
```

## Rollback

```bash
gh release delete v2.0.5 --yes
git push origin :refs/tags/v2.0.5
git tag -d v2.0.5
```
