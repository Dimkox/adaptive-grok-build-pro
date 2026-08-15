# Publish v2.0.4

Human-owned runbook. Agents must not run `git push`, `git tag`, or `gh release`.

## Checks

1. `python3 scripts/grok_status.py` — change is `ready`, evidence gaps empty
2. `make verify` (source of truth) / `python3 scripts/grok_verify.py --mode pr`
3. `python3 scripts/grok_deploy.py` — dry-run prints the commands below
4. Only when you are ready to publish: `python3 scripts/grok_approve.py production --reason "publish v2.0.4"`
5. Optional: `python3 scripts/grok_deploy.py --record` — writes receipt `deploy`/`prepared`

## Printed commands (human-owned)

`grok_deploy.py` prints the current branch. Typical sequence:

```bash
python3 scripts/package_stack.py
cp dist/adaptive-grok-build-pro-v2.0.4.zip* packages/
git tag -a v2.0.4 -m "v2.0.4"
git push origin <branch>
git push origin v2.0.4
gh release create v2.0.4 packages/adaptive-grok-build-pro-v2.0.4.zip packages/adaptive-grok-build-pro-v2.0.4.zip.sha256 --notes-file dist/RELEASE-NOTES.md
```

Do not copy a 2.0.4 zip into `packages/` until this human publish step.

## Rollback

If the GitHub Release or tag must be withdrawn:

```bash
gh release delete v2.0.4 --yes
git push origin :refs/tags/v2.0.4
git tag -d v2.0.4
```

If `packages/` was updated after a failed publish, remove the unpublished 2.0.4 zip and checksum.

## Agent rule

The agent never runs `git push`, `gh release`, `docker push`, or `npm publish`. `scripts/grok_deploy.py` only prepares and prints.
