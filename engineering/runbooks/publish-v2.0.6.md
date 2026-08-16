# Publish v2.0.6

Print-only last mile. Assemble the zip first; humans own tag / push / GitHub Release.

Agents must not run `git push`, `git tag`, or `gh release`; humans own those commands.

## Checks

```bash
python3 scripts/grok_status.py
python3 scripts/grok_verify.py --mode pr
python3 scripts/grok_deploy.py
```

Only when a human is ready to publish: `python3 scripts/grok_approve.py production --reason "publish v2.0.6"`

## Commands

```bash
python3 scripts/package_stack.py
cp dist/adaptive-grok-build-pro-v2.0.6.zip* packages/
git tag -a v2.0.6 -m "v2.0.6"
git push origin main
git push origin v2.0.6
gh release create v2.0.6 packages/adaptive-grok-build-pro-v2.0.6.zip packages/adaptive-grok-build-pro-v2.0.6.zip.sha256 --notes-file dist/RELEASE-NOTES.md
```

## Rollback

```bash
gh release delete v2.0.6 --yes
git push origin :refs/tags/v2.0.6
git tag -d v2.0.6
```
