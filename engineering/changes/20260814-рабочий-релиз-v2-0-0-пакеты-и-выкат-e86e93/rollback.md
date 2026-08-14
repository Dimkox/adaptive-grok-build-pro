# Rollback — v2.0.0

## Trigger

Broken package, leaked secret, or tag pointing at the wrong tree.

## Application rollback

```bash
gh release delete v2.0.0 --yes
git push origin :refs/tags/v2.0.0
git tag -d v2.0.0
git revert <release-commit>
git push origin main
```

## Data

No migrations. Runtime under `.grok-stack/runtime/` is local and gitignored.

## Verification after rollback

`python3 -m unittest discover -s tests` and `python3 scripts/grok_doctor.py`.
