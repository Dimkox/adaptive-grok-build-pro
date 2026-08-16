# Analysis — repo_explorer

Change: `20260816-ship-working-v2-0-6-quality-contour-ec0388`  
Route: `ec0388060302` · write=`general_implementer` · reviews=`code_reviewer`+`test_reviewer`  
Narrow question: **What exact files must change to land a working 2.0.6 quality contour without adding `pyproject.toml`?**

Read-only. No application-code edits. No `.env`. No push / tag / merge / deploy.

Approved design: [ef7b14 architecture](../../20260816-release-readiness-gap-vs-dobryakov-code-quality-ef7b14/architecture.md) + [human-approval](../../20260816-release-readiness-gap-vs-dobryakov-code-quality-ef7b14/evidence/human-approval.md). Acceptance: [analysis-task_analyst.md](analysis-task_analyst.md).

---

## Ruling (one screen)

A working 2.0.6 is **Bucket A on this tree + identity + assembled zip**. It does **not** require a GitHub tag or Latest flip.

**Must edit / add** a small vertical set (see §3). **Must not add** `pyproject.toml`, `requirements.txt`, or `setup.py`. **Must not retag** `v2.0.5`.

`VERSION` is the only machine source of truth. Packager and deploy already follow it. Bump that file and the zip name follows.

---

## 1. Current behavior of the named surfaces

### 1.1 `.grok-stack/adaptive_grok/verification.py`

`verify()` (L204–239) always runs, in order:

1. `git-diff-check`
2. `secret-scan` (three regexes on **changed** files only)
3. `contract-structure`
4. `sql-safety`
5. then conditional PHP / Bitrix / Node
6. then `_python(root)`

It **never** reads `.grok-stack/config/quality-profiles/*.json`. `active_profiles` is only used as name flags (`php`, `bitrix`, `frontend`). Wiring `required_checks` is **out of this slice**.

`_python()` (L181–201) today:

```
has_project = any(pyproject.toml | requirements.txt | setup.py)
if has_project:
    if ruff on PATH:  ruff check .
    if pytest on PATH and tests/: pytest -q; return   # skips unittest
if tests/test*.py at top level:
    python -m unittest discover -s tests
```

On **this** repo there is no packaging marker, so ruff is **dead**. The live check is `python-unittest` only. That is the 2.0.4 contract locked by `decisions.md` (2026-08-14) and `tests/test_verification_doctor.py`.

Bandit and Coverage.py are **absent** from this file. `secret-scan` must stay; Bandit is complementary AST, not a replacement.

`scripts/grok_verify.py` is a thin CLI over `verify()`. Modes: `fast` / `pr` / `release`. No coverage-skip logic yet. Design: `fast` may skip coverage fail-under; `pr`/`release` include it once measured.

### 1.2 `.grok-stack/adaptive_grok/repo.py` — `detect_repo`

L82–84 is the landmine:

```python
if (root / 'pyproject.toml').is_file() or (root / 'requirements.txt').is_file():
    languages.append('python')
    signals.append('python:project')
```

`setup.py` is **not** a `detect_repo` marker (it is a `_python` `has_project` marker). `ruff.toml`, `.bandit`, `bandit.yaml`, `.coveragerc` are **not** markers.

This product’s live route is `repo.kind=generic`, `languages=[]`, `signals=[]`. Adding `pyproject.toml` or `requirements.txt` flips the product to `kind=python` and, if pytest is on PATH, `_python` takes the pytest-wins early return and **skips** `python-unittest`.

**Do not edit `detect_repo` to treat `ruff.toml` as `python:project`.** Do not add a packaging marker to light tools.

`tests/test_repo_router.py` has no test that “this tree / a ruff.toml-only tree stays generic”. A characterization test there is recommended (P1).

### 1.3 `tests/test_verification_doctor.py` and related

Current Python-gate tests (must stay green):

| Test | Locks |
| --- | --- |
| `test_python_runs_unittest_without_project_marker` | unmarked `project_copy` + `tests/test*.py` → `python-unittest` pass |
| `test_python_unittest_failure_is_a_failed_check` | failing unittest → overall `fail` |
| `test_python_skips_without_tests_or_project_marker` | `_python` returns `[]` |
| `test_python_ignores_non_python_tests_directory` | PHP-only `tests/` → no Python check |
| `test_python_ignores_nested_unittest_without_top_level` | `tests/nested/test_*.py` is not discovery |
| `test_python_pytest_wins_when_project_marker_present` | `pyproject.toml` + pytest on PATH → `pytest`, **no** `python-unittest` |
| `test_verify_records_receipt_for_active_route` | real `verify()` writes a receipt |
| `test_secret_scan_detects_key` | regex secret-scan still works |
| `test_project_doctor_has_no_failures` | doctor on **this** tree is clean |

`project_copy` (`tests/_support.py`) copies `.grok`, `.agents`, `.grok-stack`, `AGENTS.md`, `VERSION` only. It does **not** copy `ruff.toml`, `.bandit`, `.coveragerc`, `scripts/`, or root hook shims.

Implication for the writer:

- Gate **coverage fail-under** on presence of `.coveragerc` (this repo has it; `project_copy` does not). Otherwise a host/CI `coverage` binary plus `--fail-under` will fail the tiny `_PASSING_UNITTEST` trees.
- Mock `command_exists` / `_command_check` for ruff/bandit presence tests. Do **not** call `verify(ROOT)` from inside the suite (recurses).
- If CI `pip install`s ruff/bandit **before** the unittest job, any unmocked `verify(project_copy)` will invoke real ruff/bandit on the copied `.grok-stack/adaptive_grok`. Pass only existing paths; keep product code clean under the chosen `select`.

Related tests that constrain CI / version / packaging (usually no logic edit):

- `tests/test_deploy.py::test_root_workflow_equals_template` — **byte-identical** lock between `.github/workflows/adaptive-grok.yml` and `.grok-stack/templates/ci/github-actions.yml`
- `tests/test_deploy.py::test_template_package_job_is_conditional_and_has_no_publish` — no `gh release` / `git push` / `docker push` in CI
- `tests/test_deploy.py::test_dry_run_ready_is_ok_without_receipt` — commands interpolate whatever `VERSION` says
- `tests/test_manifest_package.py::test_default_output_follows_version_file` — zip name follows `VERSION`
- `tests/test_structure.py::test_quality_profiles_are_valid` — schema only (`schema_version`, `name==stem`, `required_checks` is a list)
- `tests/test_toolchain.py::test_real_toolchain_json_required_and_optional_sets` — `python3`/`git` required; `php`/`gh`/`node` not required
- Suite size today: **156** `def test_*` methods (159 grep hits minus 3 fixtures in string literals)

### 1.4 `.github/workflows/adaptive-grok.yml`

Byte-identical to `.grok-stack/templates/ci/github-actions.yml`. Two jobs:

| Job | Steps | Publish? |
| --- | --- | --- |
| `verify` | checkout@v4, setup-python 3.12, `unittest discover -s tests`, `grok_doctor.py`, `grok_verify.py --mode pr` | no |
| `package` (needs verify, if `scripts/package_stack.py` exists) | checkout, setup-python, `package_stack.py`, upload `dist/*.zip*` | no |

No `pip install ruff/bandit/coverage`. No Dependabot. No other workflows. `.github/` contains only `workflows/adaptive-grok.yml`.

`install_into.py --with-ci` copies the **template** to consumers. Any pip-install step added here ships to `--with-ci` consumers. That is acceptable if `grok_verify` skip-if-missing-or-nothing-to-do.

Design constraint: do **not** add a third suite run. After coverage lands, either wrap unittest inside `verify()` or drop the standalone `unittest discover` step so CI is doctor + `grok_verify --mode pr`.

### 1.5 Version is `VERSION` only

| Reader | Behavior |
| --- | --- |
| `VERSION` | Single line `2.0.5`. **Source of truth.** |
| `scripts/package_stack.py` `_default_output` L36–38 | `(root / 'VERSION').read_text().strip() or '0.0.0'` → `dist/adaptive-grok-build-pro-v{version}.zip` |
| `.grok-stack/adaptive_grok/deploy.py` `_version` L13–17 | same file, OSError → `0.0.0`. Printed `git tag` / `gh release create` use this. |
| `tests/test_manifest_package.py` L52–56 | asserts default output follows the file |
| `tests/test_deploy.py` L99–107 | asserts printed commands contain `v{VERSION}` |
| `README.md` L1 | H1 `Adaptive Grok Build Pro v2.0.5` — **docs only**, not parsed |
| `CHANGELOG.md` | human history; latest heading `## 2.0.5 — 2026-08-15` |
| `packages/README.md` | table through 2.0.5 |
| `dist/RELEASE-NOTES.md` | copy of the 2.0.5 CHANGELOG section (used by `gh release --notes-file`) |
| `.grok-stack/adaptive_grok/__init__.py` | leftover `__version__ = "2.0.0"` — **not** read by packager/deploy. Optional honesty bump only. |

No `pyproject` version, no setuptools version, no git-describe. **Do not retag `v2.0.5`.** New identity is `2.0.6`.

### 1.6 `scripts/package_stack.py`

No version-logic change required. After `VERSION` is `2.0.6`, `python3 scripts/package_stack.py` writes `dist/adaptive-grok-build-pro-v2.0.6.zip` + sibling `.sha256`. Writer then `cp`s into `packages/`.

Exclusions already cover `.coverage` (`manifest.py` `EXCLUDED_FILES`), `.env` / keys, runtime state except `.gitkeep`, `__pycache__`, `*.zip`. `.gitignore` has `coverage/` and `dist/` but **not** the `.coverage` file itself — add it so a local coverage run does not dirty the tree.

Installer `MANAGED_FILES` does **not** copy `ruff.toml` / `.bandit` / `.coveragerc` into consumers. Correct: those configs are this-repo gates.

### 1.7 `quality-profiles/*.json`

Nine files, schema-validated only. `verify()` ignores the lists.

| File | Today | 2.0.6 honesty edit? |
| --- | --- | --- |
| `base.json` | required `git-diff-check`, `secret-scan`; optional `contract-structure`, `sql-safety` | **Yes** — add `ruff`, `bandit`, `coverage` under `optional_checks`. Do **not** move them to `required_checks` (that would look like `verify()` honors the list). |
| `frontend.json` | optional `npm-lint\|typecheck\|test\|build` | **No** for A. ESLint/Prettier stay consumer `npm run lint`. |
| `infra.json` | required `secret-scan` | **No** Trivy default. |
| `php.json` / `bitrix.json` / `contracts.json` / `data.json` / `integration.json` / `ai.json` | existing adapters | **No** |

Do not add a tenth profile. Do not make `verify()` load these lists.

### 1.8 `.grok-stack/config/toolchain.json`

Pins: `python3`, `git` (required); `grok`, `gh`, `node`, `npm`, `php`, `composer` (optional). **No ruff / bandit / coverage.**

`install_into.py` default pulls **required** tools only; `--all-deps` pulls optional. Adding ruff/bandit/coverage as required would make doctor fail and consumer installs pull them. Adding them as optional would surprise `--all-deps` (today that means PHP/Node/gh).

**Leave `toolchain.json` unchanged.** CI `pip install` is the fail-closed path. Local skip-if-missing.

### 1.9 Confirmed absences (still true)

At repo root / `.github/`:

- `pyproject.toml`, `requirements.txt`, `setup.py` — **must stay absent**
- `ruff.toml`, `.ruff.toml`, `bandit.yaml`, `.bandit`, `.coveragerc`, `pytest.ini`
- `.github/dependabot.yml`
- root `package.json`, root `composer.json`
- `Dockerfile`, `docker-compose*.yml`, `.semgrep.yml`, `codecov.yml`

`detect_repo` on this tree: generic. `_python` on this tree: unittest only.

---

## 2. How the A contour should attach (no packaging marker)

| Check | Gate | Local missing binary | CI | Config |
| --- | --- | --- | --- | --- |
| `ruff` | **not** `has_project`; run if `ruff` on PATH; only pass **existing** paths | `skip` | `pip install ruff` then fail-closed | **`ruff.toml`** (not pyproject). Paths: `.grok-stack/adaptive_grok`, `scripts/`, `tests/`, nine root hook shims. First landing: narrow `select` (`E`, `F`, `I` or equivalent). |
| `bandit` | not `has_project`; if `bandit` on PATH | `skip` | `pip install bandit` then fail-closed | `.bandit` or `bandit.yaml`. Exclude `tests/` noise if needed. **Does not replace `secret-scan`.** |
| coverage | if `coverage` on PATH **and** `.coveragerc` exists (so `project_copy` / consumers without that file never take fail-under) | `skip` | `pip install coverage` then fail-closed | `.coveragerc`. **Measure first.** `--fail-under` = measured − 2 (or documented floor). No Codecov. Wrap existing unittest; do not add a third run. `fast` may skip fail-under. |
| Dependabot | GitHub only | n/a | n/a | `.github/dependabot.yml`, `package-ecosystem: github-actions` weekly. **No `pip` ecosystem.** |

Pytest-wins when a **consumer** has `pyproject.toml` + pytest remains. Do not “fix” it.

Bucket B (Semgrep, Trivy image, ESLint/Prettier) is **not** default-on this repo. If any adapter is added, it must skip here (no `package.json`, no Dockerfile, no Semgrep config).

---

## 3. Exact file list

### 3.1 Must change (product)

| Path | Action | Why |
| --- | --- | --- |
| `.grok-stack/adaptive_grok/verification.py` | Edit `_python` / add `_ruff`, `_bandit`, `_coverage` | Ungate ruff; add Bandit; wrap/add coverage after measure; keep unittest on unmarked trees |
| `ruff.toml` | **Create** | This-repo Ruff config. Not a `detect_repo` marker. |
| `.bandit` **or** `bandit.yaml` | **Create** | Bandit config. Pick one. |
| `.coveragerc` | **Create after measuring** | Omit tests/runtime; record measured floor; `fail_under` = measured − 2 |
| `tests/test_verification_doctor.py` | Edit | Characterization + fail cases for ruff / bandit / coverage / secret-scan complement (task_analyst P0) |
| `.github/workflows/adaptive-grok.yml` | Edit | `pip install ruff bandit coverage` (inline; **not** `requirements.txt`); fail-closed verify; do not add a third suite run |
| `.grok-stack/templates/ci/github-actions.yml` | Edit **identically** | Locked by `test_root_workflow_equals_template` |
| `.github/dependabot.yml` | **Create** | `github-actions` only, weekly |
| `.grok-stack/config/quality-profiles/base.json` | Edit | Honest `optional_checks`: `ruff`, `bandit`, `coverage` |
| `VERSION` | `2.0.5` → `2.0.6` | Sole machine version |
| `CHANGELOG.md` | New top `## 2.0.6 — 2026-08-16` | Do not rewrite `## 2.0.5` |
| `README.md` | H1 → `v2.0.6`; mention A checks if the verify section is updated | Docs identity |
| `packages/README.md` | Add 2.0.6 row | Keep 2.0.0–2.0.5 |
| `dist/RELEASE-NOTES.md` | Replace with 2.0.6 section | `gh release --notes-file` |
| `packages/adaptive-grok-build-pro-v2.0.6.zip` + `.sha256` | Generate via `package_stack.py` then `cp` | Assembled product. Do not rebuild 2.0.5 zips. |
| `.gitignore` | Add `.coverage` (and `htmlcov/` if used) | Coverage artifacts already excluded from manifest/fingerprint, not from git |

### 3.2 Should change (docs / lock-in)

| Path | Action |
| --- | --- |
| `tests/test_repo_router.py` | Add: `ruff.toml` / `.coveragerc` alone do **not** set `python:project`; this tree stays generic |
| `tests/test_deploy.py` | Optionally assert CI contains `pip install ruff` and still has no publish |
| `tests/test_structure.py` | Optionally lock `ruff.toml` exists and `pyproject.toml` does not |
| `.grok-stack/templates/ci/README.md` | Document `pip install` + same `grok_verify` command |
| `engineering/decisions.md` | Short 2026-08-16 entry: Ruff via `ruff.toml`; never light tools with a packaging marker |
| `engineering/runbooks/publish-v2.0.6.md` | **Create** (print-only last mile). Agents do not execute it. |
| Change-package `brief.md` / `requirements.md` / `architecture.md` / `tasks.md` / `test-plan.md` / `release.md` / `rollback.md` | Writer fills from this + task_analyst. Not application code. |

### 3.3 Optional / leftover

| Path | Note |
| --- | --- |
| `.grok-stack/adaptive_grok/__init__.py` | `__version__ = "2.0.0"` leftover. Not version source. Honesty bump to `2.0.6` is optional. |
| `Makefile` | No new target required. `verify` already calls `grok_verify --mode pr`. |
| `QUICKSTART.md` | No version string today. No required edit. |
| `README.md` toolchain table | Do **not** add ruff/bandit/coverage as required host tools. |

### 3.4 Do not touch

| Path | Why |
| --- | --- |
| **`pyproject.toml` / `requirements.txt` / `setup.py`** | Forbidden. Flip `detect_repo` / pytest-wins. |
| `.grok-stack/adaptive_grok/repo.py` marker list | Do not treat quality configs as `python:project`. |
| `scripts/package_stack.py` version logic | Already reads `VERSION`. |
| `scripts/install_into.py` `MANAGED_FILES` / default dep pull | Must not start installing ruff/bandit. |
| `.grok-stack/config/toolchain.json` | Required set stays python3+git. |
| `packages/adaptive-grok-build-pro-v2.0.5.zip*` | Published 2.0.5 assets stay. |
| `engineering/runbooks/publish-v2.0.5.md` | Historical. |
| Other `quality-profiles/*.json` | B is not default-on. |
| `verify()` JSON-list wiring | Later slice, not A. |
| Bitrix core / `bitrix_checks.py` | This route is `generic`. |
| Codecov / Semgrep-default / Trivy-default / pre-commit-as-gate | Out of A. |

`requirements-ci.txt` (name **must not** be `requirements.txt`) is allowed later for pins. Not required for 2.0.6; inline `pip install ruff bandit coverage` in the workflow is enough.

---

## 4. Ruff path inventory (this tree)

`ruff.toml` should include only these, and `_ruff` should pass only paths that exist:

**Package / scripts**

- `.grok-stack/adaptive_grok/*.py` — 15 modules: `__init__`, `bitrix_checks`, `change`, `deploy`, `doctor`, `manifest`, `policy`, `receipts`, `repo`, `router`, `state`, `toolchain`, `util`, `verification`
- `scripts/*.py` — `grok_{approve,change,deploy,doctor,review,route,status,verify}.py`, `install_into.py`, `package_stack.py`, `generate_manifest.py`, `verify_manifest.py`

**Root hook shims** (thin dispatchers; `test_structure.py` locks them)

- `session_start.py`, `session_end.py`, `user_prompt_submit.py`, `pre_tool_use.py`, `post_tool_use.py`, `pre_compact.py`, `subagent_start.py`, `subagent_stop.py`, `stop_gate.py`

**Tests**

- `tests/*.py` — 12 modules + `_support.py`

Exclude: `.grok-stack/runtime`, `dist/`, `packages/`, `examples/` (PHP), `__pycache__`. `scripts/bootstrap.sh` / `bootstrap.ps1` are not Python.

Architect residual: first `select` must be narrow enough that this inventory is green on the ship tree.

---

## 5. Coverage baseline — **unmeasured**

No `coverage run` exists in CI or `verify()`. Ignore rules already anticipate artifacts (`.gitignore` `coverage/`; `manifest.py` `.coverage`; `util._fingerprint_noise` `.coverage` and `coverage/`).

Writer **must** measure line coverage on `.grok-stack/adaptive_grok` + `scripts` **before** writing `--fail-under`. Do not invent 90%. Record the number in `.coveragerc` and CHANGELOG 2.0.6.

Suggested wrap (does not add a third run):

- `_python` keeps the `python-unittest` check name.
- When `coverage` exists **and** `.coveragerc` exists **and** mode is `pr`/`release`: command becomes `coverage run -m unittest discover -s tests` then `coverage report`.
- CI drops standalone `unittest discover` **or** that step *is* the coverage wrap — not both plus `grok_verify` unittest.

---

## 6. Impact on consumers

| Mechanism | Effect after A |
| --- | --- |
| `install_into` default | Copies `.grok-stack` (new `verify()` logic) and scripts. Does **not** copy `ruff.toml` / `.bandit` / `.coveragerc`. Does **not** pull ruff/bandit if `toolchain.json` is left alone. |
| `install_into --with-ci` | Gets the updated template, including `pip install ruff bandit coverage` + `grok_verify`. Safe if checks skip when binaries/paths/configs are absent or empty. |
| Consumer with `ruff` on PATH | New `ruff` check may fire. Pass only existing paths. |
| Consumer with `pyproject.toml` + pytest | Unchanged pytest-wins. Ruff also fires if binary present (no longer gated on the marker — good). |
| This product `detect_repo` | Must remain `generic`. |

---

## 7. Suggested implementation order (writer)

Matches approved A-order and “failing test first”:

1. Characterization tests for unmarked-tree unittest + ruff skip/present (must fail or skip-check today).
2. `ruff.toml` + ungate `_ruff` + CI `pip install ruff`. Make this tree green on the narrow rule set.
3. Bandit tests + `.bandit`/`bandit.yaml` + `_bandit`. Prove `secret-scan` still fails a planted secret.
4. **Measure** coverage. Write `.coveragerc` with the real floor. Wrap unittest. Adjust CI so the suite is not triple-run.
5. `.github/dependabot.yml`.
6. `base.json` optional_checks honesty.
7. Identity: `VERSION`, CHANGELOG, README, packages README, RELEASE-NOTES.
8. `python3 scripts/package_stack.py` and `cp` to `packages/`.
9. Fill change-package docs. Transition `ready` **then** record verification/reviews (`decisions.md` 2026-08-14).

Do not run `git tag` / `git push` / `gh release create`. Last mile stays `python3 scripts/grok_deploy.py`.

---

## Sources inspected

- `.grok-stack/runtime/active-route.json`
- `.grok-stack/adaptive_grok/{verification,repo,deploy,doctor,manifest,util,toolchain,__init__}.py`
- `scripts/{grok_verify,package_stack,install_into}.py`
- `tests/{test_verification_doctor,test_deploy,test_manifest_package,test_structure,test_toolchain,test_repo_router,test_installer,_support}.py`
- `.github/workflows/adaptive-grok.yml`, `.grok-stack/templates/ci/{github-actions.yml,README.md}`
- `.grok-stack/config/{toolchain.json,quality-profiles/*.json}`
- `VERSION`, `CHANGELOG.md`, `README.md`, `packages/README.md`, `dist/RELEASE-NOTES.md`, `Makefile`, `.gitignore`
- Prior design: `engineering/changes/20260816-release-readiness-gap-vs-dobryakov-code-quality-ef7b14/{architecture,requirements,evidence/*}`
- `engineering/decisions.md` 2026-08-14 (no packaging marker)

Confirmed missing at inspection time: `pyproject.toml`, `requirements.txt`, `setup.py`, `ruff.toml`, `.bandit`, `bandit.yaml`, `.coveragerc`, `.github/dependabot.yml`.
