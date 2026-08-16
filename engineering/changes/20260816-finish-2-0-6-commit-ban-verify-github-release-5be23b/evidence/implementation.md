# Implementation — commit GHA ban as unpublished 2.0.6

Write owner: `general_implementer`  
Route: `5be23b16d59f`  
Change: `20260816-finish-2-0-6-commit-ban-verify-github-release-5be23b`

No product edits. No `package_stack.py`. No tag / push / `gh release`.

## New SHA

```
e75f3a1b92e247279fbb6210d46715a90cf7895c
```

Short: `e75f3a1`

Parent: `549f29da1c4ff44ba44d8388c294fd5dd29bfd81`  
Message: `Release v2.0.6: ban GitHub Actions, rebuild zip`

`HEAD` ≠ `549f29d`. `549f29d` is an ancestor. No `refs/tags/v2.0.6`.

## What was committed

Pathspecs only (`git add -A` not used).

Deleted in `e75f3a1`:
- `.github/workflows/adaptive-grok.yml`
- `.github/dependabot.yml`
- `.grok-stack/templates/ci/github-actions.yml`

`git show HEAD:.github/workflows/adaptive-grok.yml` fails (file not in commit).

Included:
- `.grok-stack/templates/ci/README.md`
- `CHANGELOG.md`
- `engineering/decisions.md`
- `engineering/runbooks/publish-v2.0.6.md`
- `scripts/install_into.py`
- `tests/test_deploy.py`
- `tests/test_installer.py`
- `tests/test_manifest_package.py`
- `tests/test_structure.py`
- `packages/adaptive-grok-build-pro-v2.0.6.zip`
- `packages/adaptive-grok-build-pro-v2.0.6.zip.sha256`
- `engineering/changes/20260816-ban-gha-rebuild-and-verify-2-0-6-publish-9fd274/`
- `engineering/changes/20260816-finish-2-0-6-commit-ban-verify-github-release-5be23b/` (this file written after the commit; left uncommitted)

## Not staged

- leftover `ad4090` evidence / `requirements.md` / `state.json`
- `864726`
- `39b13f`
- `cd8a96`
- `ec0388` leftover reviews / `state.json`
- root `MANIFEST.sha256` (absent)
- `.env`
- `.grok-stack/runtime/**`
- `pyproject.toml` / `requirements.txt` / `setup.py` (absent)
- `packages/…v2.0.5.zip*`
- `VERSION` (already `2.0.6`)

## Identity and zip

- `VERSION` in commit: `2.0.6`
- Tracked zip digest: `55406ff22f81ae05fc70eb9a5710b5c055c76a18f2ddbe60687c03b3e0b95c4d`
- v2.0.5 zip untouched: `b80e63103453db3161a4e4489216f654c04aec27e0821a1642ccc6c37027b4fd`

## Left for controller

1. `python3 scripts/grok_verify.py --mode pr` on `e75f3a1`
2. Independent `code_reviewer` + `test_reviewer` on the commit vs `549f29d`
3. Last mile on **`e75f3a1`**, not `549f29d`: fresh `grok_approve.py production`, tag `v2.0.6`, push `main`, push tag, `gh release create`
