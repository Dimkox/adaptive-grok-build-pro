# Code review — ship working v2.0.6 quality contour

Change: `20260816-ship-working-v2-0-6-quality-contour-ec0388`  
Route: `ec0388060302` · reviewer: `code_reviewer` (read-only) · write owner: `general_implementer`  
Reviewed: 2026-08-16

**PASS.** I would not block.

I did not trust `evidence/implementation.md`. Inspected the live `549f29d` working tree, surrounding implementation, change-package contracts, and git refs. This reviewer session has no shell, so there is no live `git show` / `git ls-files` / `ruff` / `bandit` / `coverage` / `sha256sum`. Equivalents are listed below.

---

## Verdict against the nine checks

| # | Check | Result |
| --- | --- | --- |
| 1 | No `pyproject.toml` / `requirements.txt` / `setup.py` | **PASS** |
| 2 | ruff/bandit not gated on packaging markers; run before pytest-wins | **PASS** |
| 3 | bandit does not replace `secret-scan` | **PASS** |
| 4 | Bucket B is skip-unless-signal; this tree emits none of those checks | **PASS** |
| 5 | CI template == root workflow; no publish job | **PASS** |
| 6 | Dependabot is `github-actions` only | **PASS** |
| 7 | VERSION 2.0.6; zip tracked; v2.0.5 tag not rewritten | **PASS** |
| 8 | No new service / SaaS | **PASS** |
| 9 | Residual risk / would you block? | Residuals only. **No block.** |

Would I block? **No.**

---

## What was actually inspected

```text
# refs (git rev-parse / tag equivalents)
read .git/HEAD                          → ref: refs/heads/main
read .git/refs/heads/main               → 549f29da1c4ff44ba44d8388c294fd5dd29bfd81
read .git/refs/remotes/origin/main      → 7c0ae7573535ddd0cfe3800f81278991ced81584
read .git/COMMIT_EDITMSG                → Release v2.0.6: ruff, bandit, coverage, dependabot
read .git/logs/HEAD                     → 7c0ae75 → 549f29d  commit: Release v2.0.6…
read .git/refs/tags/                    → v2.0.0 … v2.0.5 only; no v2.0.6
read .git/refs/tags/v2.0.5              → 7f85f7be43fd8008f6af522a967ebc5268a481d1
                                          (same annotated object as cd8a96; not retargeted to 549f29d)

# contracts
engineering/changes/…-ec0388/{brief,architecture,requirements,tasks,test-plan,release,rollback}.md
engineering/changes/…-ec0388/evidence/{analysis-architect,implementation,coverage-baseline,ruff-first-run}.md
prior ef7b14 architecture (A then B; no pyproject; no SaaS)

# product
.grok-stack/adaptive_grok/verification.py   (_ruff/_bandit/_python/_semgrep/_trivy_config/_node/verify)
.grok-stack/adaptive_grok/{manifest,repo,policy,router,toolchain,util}.py
ruff.toml  bandit.yaml  .coveragerc  VERSION  CHANGELOG.md  README.md
.github/workflows/adaptive-grok.yml
.grok-stack/templates/ci/github-actions.yml
.github/dependabot.yml
.grok-stack/config/quality-profiles/{base,frontend,infra,ai,bitrix,php,contracts,data,integration}.json
.grok-stack/config/toolchain.json
scripts/{grok_verify,install_into,package_stack}.py
Makefile  .gitignore
packages/README.md  dist/RELEASE-NOTES.md
packages/adaptive-grok-build-pro-v2.0.6.zip.sha256
packages/adaptive-grok-build-pro-v2.0.5.zip.sha256
engineering/runbooks/publish-v2.0.6.md
engineering/decisions.md

# tests
tests/test_verification_doctor.py
tests/test_deploy.py
tests/test_structure.py
tests/test_manifest_package.py
tests/_support.py

# absences (read of each path → does not exist)
pyproject.toml  requirements.txt  setup.py
package.json  Dockerfile  dockerfile  Containerfile
semgrep.yaml  .semgrep.yml  .semgrep.yaml  .semgrep/
docker-compose.yml
```

`origin/main` is still `7c0ae75`. Local `main` is `549f29d`. No push, no `v2.0.6` tag. Matches the assemble-only contract.

---

## 1. No packaging markers — PASS

Root listing and targeted reads: `pyproject.toml`, `requirements.txt`, and `setup.py` are absent.

Locked by `tests/test_structure.py::test_product_tree_has_no_packaging_markers`.

`detect_repo` still only treats `pyproject.toml` / `requirements.txt` as `python:project`. `ruff.toml`, `bandit.yaml`, and `.coveragerc` are not markers. Live route remains `repo.kind=generic`.

CI pins live inline in the workflow (`pip install 'ruff>=0.6,<1' 'bandit>=1.7,<2' 'coverage>=7,<8'`), not in a `requirements.txt`.

---

## 2. ruff/bandit not marker-gated; before pytest-wins — PASS

`_python` now starts with independent checks, then the old marker/pytest branch:

```257:269:.grok-stack/adaptive_grok/verification.py
def _python(root: Path, mode: str = 'fast') -> list[CheckResult]:
    results: list[CheckResult] = [_ruff(root), _bandit(root)]
    has_project = any((root / item).exists() for item in ('pyproject.toml', 'requirements.txt', 'setup.py'))
    tests_dir = root / 'tests'
    has_unittest_files = tests_dir.is_dir() and any(tests_dir.glob('test*.py'))
    if has_project and command_exists('pytest') and tests_dir.is_dir():
        results.append(_command_check(root, 'pytest', ['pytest', '-q'], 900))
        ...
        return results
```

- Old marker-gated `ruff check .` is gone.
- `_ruff` / `_bandit` skip if the binary is missing or no quality paths exist; they do not fail-closed locally.
- `_ruff` command is `ruff check <existing QUALITY_PY_PATHS>`, not `ruff check .`.
- pytest-wins still returns early **after** ruff/bandit. Characterization: `test_python_pytest_wins_when_project_marker_present` and `test_pytest_wins_but_ruff_and_bandit_run_first`.
- Marker-less + ruff still emits `python-unittest`: `test_unmarked_tree_with_ruff_still_runs_unittest`.

`ruff.toml` is the conservative architect set (`E4 E7 E9 F`, `ignore = ["E402"]`, no isort, no `E501`). First-run evidence (8 F401, then clean) is consistent with the F401-only import edits in `policy.py`, `repo.py`, `router.py`, `toolchain.py`, `verification.py`, `scripts/package_stack.py`, `tests/test_toolchain.py`, `tests/_support.py`. Those files still look like unused-import deletions, not behavior changes.

---

## 3. Bandit does not replace secret-scan — PASS

`verify()` still always prepends `_secret_scan(root, files)` before any quality adapters. `_bandit` is a separate check on product paths only (`tests` stripped from the path list; `bandit.yaml` also `exclude_dirs: tests` / `engineering`).

Complement tests:

- `test_missing_bandit_is_skip_and_secret_scan_remains`
- `test_secret_scan_still_fails_when_bandit_present` (uses `changed_files` untracked list, which includes the planted `config.php`)
- `test_eval_in_product_path_fails_bandit`
- `test_eval_only_in_tests_does_not_fail_bandit`

Skips are the architect set (`B101 B404 B603 B607`). `B307` / `B602` / `B105` stay on. Grep of `.grok-stack/adaptive_grok` and `scripts` found no `eval(`, `shell=True`, or `hashlib.md5`.

`secret-scan` is still changed-files regex. That is complementary, not replaced.

---

## 4. Bucket B skip-unless-signal; this tree emits none — PASS

| Adapter | Signal | This tree | Emit |
| --- | --- | --- | --- |
| `semgrep` | `semgrep.yaml` / `.semgrep.yml` / `.semgrep.yaml` / non-empty `.semgrep/` | none exist | `_semgrep` returns `None` (not emitted) |
| `trivy-config` | `Dockerfile` / `dockerfile` / `Containerfile` / root `docker-compose*.yml(l)` | none exist | `_trivy_config` returns `None` |
| `npm-prettier` / `npm-format` | root `package.json` script | no `package.json` | `_node` not called on `base` |

Commands stay consumer-local: `semgrep scan --error --config <detected>` (never `--config auto`); `trivy config --exit-code 1 .` (never `trivy image`); `npm run prettier` / `npm run format` (never `npx`).

Missing binary + present signal = `skip`. Covered: `test_this_repo_shaped_tree_omits_bucket_b`, `test_semgrep_signal_without_binary_is_skip`, `test_trivy_signal_without_binary_is_skip`, `test_npm_prettier_emitted_when_script_present`.

Profile JSON lists the new names under `optional_checks` only. `verify()` still does not load `required_checks` / `optional_checks`. `base.json` did not promote `ruff`/`bandit`/`coverage`/`semgrep` to required.

---

## 5. CI template == root workflow; no publish — PASS

`.github/workflows/adaptive-grok.yml` and `.grok-stack/templates/ci/github-actions.yml` are the same 40-line file (read both in full). Locked by `test_root_workflow_equals_template`.

Jobs: `verify` (setup-python 3.12 → pip install the three tools → unittest discover → doctor → `grok_verify --mode pr`) and conditional `package` (`hashFiles('scripts/package_stack.py')`, `upload-artifact` of `dist/*.zip*` only).

No `gh release`, `git push`, or `docker push`. Locked by `test_template_package_job_is_conditional_and_has_no_publish` and `test_workflow_installs_quality_tools`.

Two suite executions max (CI fail-fast unittest + verify’s coverage-wrapped unittest). No third run. `fast` does not wrap or fail-under coverage.

---

## 6. Dependabot is github-actions only — PASS

`.github/dependabot.yml`:

```yaml
version: 2
updates:
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
```

No `pip` ecosystem. `.github/` contains only this file and `workflows/adaptive-grok.yml`.

---

## 7. VERSION 2.0.6; zip tracked; v2.0.5 not rewritten — PASS

| Artifact | Observed |
| --- | --- |
| `VERSION` | `2.0.6` |
| README H1 | `# Adaptive Grok Build Pro v2.0.6` |
| CHANGELOG | new `## 2.0.6 — 2026-08-16`; `## 2.0.5` and older left intact |
| `dist/RELEASE-NOTES.md` | 2.0.6 section only |
| `packages/README.md` | 2.0.6 row added; 2.0.0–2.0.5 kept |
| `make package` | still `python3 scripts/package_stack.py` |
| default zip name | `test_default_output_follows_version_file` still binds to `VERSION` |

Sibling checksums (read, not rehashed):

```
b34af685c8d277aafcfbc4aa3f393286b12af2b092e5efa2b74ab6f5ba41b610  adaptive-grok-build-pro-v2.0.6.zip
b80e63103453db3161a4e4489216f654c04aec27e0821a1642ccc6c37027b4fd  adaptive-grok-build-pro-v2.0.5.zip
```

2.0.5 zip digest is unchanged from cd8a96. `packages/adaptive-grok-build-pro-v2.0.6.zip` and `.sha256` exist. `.gitignore` ignores `dist/`, not `packages/`. `MANIFEST.sha256` includes `ruff.toml`, `bandit.yaml`, `.coveragerc`, `.github/dependabot.yml`. Manifest excludes `.coverage` / `.coverage.*` (not `.coveragerc`), `htmlcov`, `.ruff_cache`.

Limitation: no shell `git ls-files` / `sha256sum` / unzip of `VERSION` inside the zip (zip is binary). The files sit at the tracked `packages/` path on the release commit; 2.0.5 digest was not rebuilt.

Tag surface:

- local tags stop at `v2.0.5`
- `v2.0.5` ref is still annotated object `7f85f7be…` (cd8a96 peeled that to `7c0ae75`)
- no `v2.0.6` tag
- `origin/main` still `7c0ae75`

`engineering/runbooks/publish-v2.0.6.md` is print-only. `deploy.py` / `grok_deploy.py` still do not import subprocess.

---

## 8. No new service / SaaS — PASS

- `adaptive_grok` still stdlib + local modules. No `import ruff` / `import bandit` / `import coverage`.
- `toolchain.json` still python3 / git / grok / gh / node / npm / php / composer. No ruff/bandit/coverage.
- `install_into.py` does not mention those tools and does not pull them.
- No Codecov, Semgrep SaaS, Sonar, Snyk, Datadog, Sentry, or other Bucket C.
- No new Docker service, database, queue, or paid SKU.
- Quality-profile JSON is documentation. `verify()` stays hardcoded.

---

## Findings

No functional, security, or scope-break findings that fail the 2.0.6 contour.

### Nits (do not fail)

1. **`test_unused_import_in_quality_path_fails_ruff`** calls `_python`, not `verify()`, so it does not lock “overall status = fail”. Wiring of the ruff check is still tested.
2. **Coverage fail-under test** uses a fake `coverage report` that always exits 1. It locks pr-mode fail-closed, not the numeric `74` in `.coveragerc`. The number is independently recorded in `evidence/coverage-baseline.md` and the rc file.
3. **`install_into` does not copy** root `ruff.toml` / `bandit.yaml` / `.coveragerc`. That is allowed (`install_into` must not start offering the tools). Consumers who already have those CLIs on PATH and no configs can fail-close; this product tree and the assembled zip include the configs.
4. **`coverage run --rcfile=.coveragerc`** is unconditional in `pr`/`release` when the binary exists. A consumer without `.coveragerc` would fail `python-unittest` rather than skip `coverage`. This tree has the rc file.

---

## Residual risk

- Profile JSON is still documentation; `verify()` does not load `required_checks`.
- `secret-scan` remains changed-files regex; Bandit is the complementary whole-path AST.
- Local skip-if-missing: a developer without ruff/bandit/coverage does not fail-close. CI installs them and fail-closes. Intended.
- Coverage ratchet is 74 (`floor(76) - 2`), not a handbook 90. Scripts CLI wrappers stay mostly uncovered. I did not re-measure the 76%.
- Assembled `packages/v2.0.6.zip` is not GitHub Latest until a human `grok_deploy`. `origin/main` is still `7c0ae75` / published `v2.0.5`.
- `fast` omits the `coverage` check entirely (architect allowed skip *or* omit).
- Could not independently peel `v2.0.5^{}` (zlib tag object) or rehash the zip. Tag object SHA and 2.0.5 digest are unchanged vs the last published wave.

Rollback in the change package is revert-the-ship-commit and leave `v2.0.5` alone. Correct.

---

## Recommendation

**PASS.** Residuals and nits only. The 2.0.6 quality contour on this tree matches the approved A + thin skip-unless-signal B design. Do not tag, push, or `gh release` from review.
