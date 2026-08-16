# Implementation — ban GHA, rebuild and verify 2.0.6

Write owner: `general_implementer`  
Route: `9fd2741e5d1b`  
Change: `20260816-ban-gha-rebuild-and-verify-2-0-6-publish-9fd274`

Not closed. Independent reviews and last mile (`git tag` / `git push` / `gh release`) are for the controller after this report.

Identity stayed `VERSION` **2.0.6**. No `pyproject.toml`.

## What landed

This repo and the installer no longer ship GitHub Actions. `--with-ci` is a hard `SystemExit` containing `forbidden`. Local `python3 scripts/grok_verify.py --mode pr` is the only gate. Unpublished 2.0.6 zip was rebuilt without workflows.

## Files

### Deleted
- `.github/workflows/adaptive-grok.yml`
- `.github/dependabot.yml`
- `.grok-stack/templates/ci/github-actions.yml`

`.github/` is gone (empty dir is not tracked).

### Tests first (inverted old contract)
- `tests/test_deploy.py` — no `adaptive-grok.yml`; no `github-actions.yml`; no `.github/workflows/*.yml`; no Dependabot; CI README bans GitHub Actions and is not a `gh release` / `git push` / `docker push` publisher
- `tests/test_installer.py` — `--with-ci` and `--with-ci --dry-run` raise `SystemExit` / `forbidden`, do not create `adaptive-grok.yml`, leave `existing.yml` untouched; default install does not copy any workflow from `.grok-stack`
- `tests/test_structure.py` — `VERSION` is `2.0.6`; no workflows / Dependabot / template YAML
- `tests/test_manifest_package.py` — `included_files()` and shipped zip have no `.github/workflows/`, no Dependabot, no `github-actions.yml`; in-zip `VERSION` is `2.0.6`

### Product
- `scripts/install_into.py` — `with_ci=True` raises at the start of `install()` (`GitHub Actions is forbidden…`); copy block removed; `--with-ci` flag kept so callers get an explicit error

### Docs
- `.grok-stack/templates/ci/README.md` — never GitHub Actions; local `make doctor` / `make verify` / `python3 scripts/grok_verify.py --mode pr` only; no other CI vendor
- `engineering/decisions.md` — 2026-08-16 never GitHub Actions
- `CHANGELOG.md` §2.0.6 — dropped Dependabot-for-GHA and “CI fail-closed after pip install”; local verify fail-closed when ruff/bandit/coverage are installed; `--with-ci` forbidden
- `dist/RELEASE-NOTES.md` — same 2.0.6 notes (gitignored scratch)
- `engineering/runbooks/publish-v2.0.6.md` — last mile is still `gh release create` (GitHub CLI), not Actions
- Root `README.md` / `QUICKSTART.md` — no Actions workflow mentions; left unchanged

### Package
- `packages/adaptive-grok-build-pro-v2.0.6.zip`
- `packages/adaptive-grok-build-pro-v2.0.6.zip.sha256`
- `VERSION` not touched (`2.0.6`)
- `packages/…-v2.0.5.*` not touched

## New zip digest

```
55406ff22f81ae05fc70eb9a5710b5c055c76a18f2ddbe60687c03b3e0b95c4d  adaptive-grok-build-pro-v2.0.6.zip
```

Previous unpublished digest `b34af685c8d277aafcfbc4aa3f393286b12af2b092e5efa2b74ab6f5ba41b610` is stale.

In-zip `adaptive-grok-build-pro/VERSION` is `2.0.6`. Namelist has no `.github/workflows`, no `dependabot.yml`, no `github-actions.yml`.

v2.0.5 zip digest unchanged: `b80e63103453db3161a4e4489216f654c04aec27e0821a1642ccc6c37027b4fd`.

## Commands

```bash
python3 scripts/package_stack.py
cp dist/adaptive-grok-build-pro-v2.0.6.zip* packages/
# from packages/:
sha256sum -c adaptive-grok-build-pro-v2.0.6.zip.sha256
python3 -m unittest tests.test_deploy tests.test_installer tests.test_manifest_package tests.test_verification_doctor -q
python3 -m unittest discover -s tests -q
python3 scripts/grok_verify.py --mode pr
```

Root untracked `MANIFEST.sha256` from `package_stack` was deleted after verify (do not commit it).

Not run: `git tag`, `git push`, `gh release`.

## Test results

| Command | Result |
| --- | --- |
| Inverted GHA tests on pre-ban tree | 7 fail + 1 error (expected TDD red) |
| Focused: `test_deploy` `test_installer` `test_manifest_package` `test_verification_doctor` | **64 tests OK** |
| `python3 -m unittest discover -s tests -q` | **177 tests OK** |
| `python3 scripts/grok_verify.py --mode pr` | **PASS** — git-diff-check, secret-scan, contract-structure, sql-safety, ruff, bandit, python-unittest, coverage; `profiles=base` |

`--with-ci` SystemExit message: `GitHub Actions is forbidden. Use local \`make verify\` / \`python3 scripts/grok_verify.py --mode pr\`.`

## Left for controller

1. Independent `code_reviewer` + `test_reviewer` on the actual diff.
2. Transition this package to `ready`, then bind receipts.
3. Last mile on the **post-ban** SHA (successor of `549f29d`), not `549f29d`: tag `v2.0.6`, push `main`, push tag, `gh release create` with the rebuilt zip. Fresh `grok_approve.py production` required.
