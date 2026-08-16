# Implementation — working 2.0.6 quality contour

Write owner: `general_implementer`  
Route: `ec0388060302`  
Change: `20260816-ship-working-v2-0-6-quality-contour-ec0388`

Not closed. Reviews and `ready` are for the controller after this report.

## What landed

One vertical: first-class Ruff / Bandit / Coverage in `grok_verify`, skip-unless-signal Semgrep / Trivy-config / npm prettier|format, Dependabot for GitHub Actions, identity 2.0.6, assembled zip.

`verify()` is still hardcoded. Quality-profile JSON lists the new names as `optional_checks` only.

## Files

### Tests
- `tests/test_verification_doctor.py` — characterization + fail cases (marker-less + ruff still unittest; pytest-wins after ruff/bandit; unused import; eval in product vs tests; secret-scan complement; coverage skip/fail-under/fast; Bucket B omit/skip; npm-prettier)
- `tests/test_deploy.py` — workflow installs ruff/bandit/coverage; still no publish
- `tests/test_structure.py` — no `pyproject.toml` / `requirements.txt` / `setup.py`
- `tests/_support.py` — copy `ruff.toml` / `bandit.yaml` / `.coveragerc` into fixtures

### Product
- `.grok-stack/adaptive_grok/verification.py` — `QUALITY_PY_PATHS`; ruff/bandit always (skip if missing); run before pytest-wins return; coverage wraps unittest in `pr`/`release` only; `_semgrep` / `_trivy_config`; `_node` prettier|format
- `.grok-stack/adaptive_grok/manifest.py` — exclude `htmlcov`, `.ruff_cache`, `.coverage` / `.coverage.*` (not `.coveragerc`)
- F401-only edits: `policy.py`, `repo.py`, `router.py`, `toolchain.py`, `scripts/package_stack.py`, `tests/test_toolchain.py`

### Config
- `ruff.toml` — E4 E7 E9 F, ignore E402, no isort, no E501
- `bandit.yaml` — exclude tests/engineering/…; skip B101 B404 B603 B607
- `.coveragerc` — measured `fail_under = 74`
- `.github/dependabot.yml` — `github-actions` weekly only
- `.gitignore` — `.coverage`, `.coverage.*`, `htmlcov/`, `.ruff_cache/`
- `.grok-stack/config/quality-profiles/base.json` — optional ruff, bandit, coverage, semgrep
- `frontend.json` — optional npm-prettier, npm-format
- `infra.json` — optional trivy-config

### CI (byte-identical)
- `.github/workflows/adaptive-grok.yml`
- `.grok-stack/templates/ci/github-actions.yml`
- Quality tools step: `pip install 'ruff>=0.6,<1' 'bandit>=1.7,<2' 'coverage>=7,<8'`
- Still one fail-fast unittest + `grok_verify --mode pr`. No publish job.

### Identity + package
- `VERSION` → `2.0.6`
- `CHANGELOG.md` new `## 2.0.6 — 2026-08-16`
- `README.md` H1 v2.0.6; honest mention of new checks
- `packages/README.md` 2.0.6 row
- `dist/RELEASE-NOTES.md` 2.0.6 section
- `engineering/runbooks/publish-v2.0.6.md` print-only last mile
- `engineering/decisions.md` — ruff.toml not pyproject
- `packages/adaptive-grok-build-pro-v2.0.6.zip` + sibling `.sha256`

## Commands

```bash
python3 -m pip install --user --break-system-packages 'ruff>=0.6,<1' 'bandit>=1.7,<2' 'coverage>=7,<8'
ruff check .grok-stack/adaptive_grok scripts tests .grok/hooks <hook shims>
bandit -c bandit.yaml -q -r .grok-stack/adaptive_grok scripts .grok/hooks <hook shims>
python3 -m coverage run --rcfile=.coveragerc -m unittest discover -s tests
python3 -m coverage report
python3 scripts/package_stack.py
cp dist/adaptive-grok-build-pro-v2.0.6.zip* packages/
sha256sum -c packages/adaptive-grok-build-pro-v2.0.6.zip.sha256
python3 -m unittest tests.test_verification_doctor tests.test_deploy tests.test_manifest_package -q
python3 -m unittest discover -s tests -q
```

Not run: `git tag`, `git push`, `gh release`, force-push, retag v2.0.5.

## Coverage number

- coverage 7.15.4
- TOTAL line **76%**
- `fail_under = 74` (`floor(76) - 2`)
- Evidence: `evidence/coverage-baseline.md`
- Ruff first run: exit 1, 8 F401; after fixes exit 0. Evidence: `evidence/ruff-first-run.md`
- Bandit first run: exit 0, no findings to fix

## Zip digest

`b34af685c8d277aafcfbc4aa3f393286b12af2b092e5efa2b74ab6f5ba41b610  adaptive-grok-build-pro-v2.0.6.zip`

- In-zip `VERSION` is `2.0.6`
- No `.env` / `err.log` / keys
- Prefix `adaptive-grok-build-pro/`
- Includes `ruff.toml`, `bandit.yaml`, `.coveragerc`, Dependabot

## Residual risk

- Profile JSON is still documentation; `verify()` does not load `required_checks`
- `secret-scan` is still changed-files only; Bandit is the complementary whole-path AST
- Assembled `packages/v2.0.6.zip` is not GitHub Latest until a human `grok_deploy`
- Coverage ratchet is 74, not a handbook 90; scripts CLI wrappers stay mostly uncovered
- Local skip-if-missing means a developer without ruff/bandit/coverage does not fail-close; CI installs them

## Rollback

Revert this change. Leave tag `v2.0.5` and Release `v2.0.5` untouched. If a later human published 2.0.6: `gh release delete v2.0.6 --yes` and delete the tag. See `rollback.md` and `engineering/runbooks/publish-v2.0.6.md`.
