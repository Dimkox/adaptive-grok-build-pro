# Analysis — architect

Change: `20260816-ship-working-v2-0-6-quality-contour-ec0388`  
Route: `ec0388060302` · write=`general_implementer` · reviews=`code_reviewer`+`test_reviewer`  
Prior approved design: `engineering/changes/20260816-release-readiness-gap-vs-dobryakov-code-quality-ef7b14/architecture.md`  
Human approval (ef7b14): Bucket A on this repo + later optional consumer B. No handbook dump. No `pyproject.toml`. No retag of 2.0.5.

Read-only. No application-code edits. No `.env`. No push / tag / merge / deploy.

Narrow question: how should `general_implementer` implement **working 2.0.6** as one coherent vertical without `pyproject.toml` and without new services?

---

## Ruling (one screen)

**One write owner. One vertical. Assemble working 2.0.6 = full Bucket A + thin B skip-unless-signal adapters + identity + zip.**

This supersedes the older ef7b14 “stop after Ruff-only” slice. That was the smallest *later* «делай». The user now said «всё полностью до рабочей версии 2.0.6 собирай», and this brief names Bandit, measured coverage, Dependabot, consumer signal adapters, CI, and packaging. That is the 2.0.6 contour. It is still **not** a handbook dump.

| In | Out |
| --- | --- |
| First-class `ruff` / `bandit` / `coverage` in `verify()`, not gated on packaging markers | `pyproject.toml`, `requirements.txt`, `setup.py` |
| Local skip-if-missing; CI `pip install ruff bandit coverage` then same `python scripts/grok_verify.py --mode pr` | Parallel CI-only quality bar |
| Dependabot `github-actions` only | Dependabot `pip`; Codecov; toolchain.json required tools |
| Semgrep / Trivy-config / npm prettier|format: emit only on consumer signals; **skip or absent on this tree** | Default-on Semgrep/Trivy/ESLint here; `trivy image` (needs a built image) |
| `VERSION` 2.0.6, CHANGELOG, README, `packages/` zip | Tag / push / `gh release`; retag 2.0.5 |
| Honest `optional_checks` names in profile JSON | Rewrite `verify()` to load `required_checks` |
| Stdlib-only `adaptive_grok`; host CLIs only | New service, DB, paid SaaS, Bucket C |

Last mile remains `python3 scripts/grok_deploy.py`. Humans own printed tag/push/release.

---

## 1. Exact `grok_verify` check names and skip vs fail

Keep the existing hardcoded core. Do **not** make `verify()` read quality-profile JSON. Add three product checks plus three consumer adapters beside the current `_python` / `_node` families.

### 1.1 Always-on core (unchanged)

| Name | Skip | Fail | Pass |
| --- | --- | --- | --- |
| `git-diff-check` | `git` missing | `git diff --check` non-zero | clean |
| `secret-scan` | never (empty file list → 0 findings) | regex hit on changed files | 0 findings |
| `contract-structure` | never (0 contracts → pass) | invalid JSON / missing openapi|asyncapi shape | ok |
| `sql-safety` | never (0 SQL → pass) | destructive/unbounded SQL regex | 0 findings |

Bandit does **not** replace `secret-scan`.

### 1.2 Product Python quality (this repo + any installed stack)

Check names are exact. Reuse `ruff` (already used when a marker exists). Do **not** invent `ruff-check` / `python-ruff`.

**Shared path set** (`QUALITY_PY_PATHS`). Include a path only if it exists on the consumer root:

```
.grok-stack/adaptive_grok
scripts
tests
.grok/hooks
user_prompt_submit.py
pre_tool_use.py
post_tool_use.py
pre_compact.py
session_start.py
session_end.py
stop_gate.py
subagent_start.py
subagent_stop.py
```

`.grok/hooks/` is the real hook logic; root files are thin shims. Both belong in 2.0.6.

| Name | When emitted | Skip | Fail | Notes |
| --- | --- | --- | --- | --- |
| `ruff` | always (product is Python, and install-into copies these paths) | `ruff` not on PATH; **or** none of `QUALITY_PY_PATHS` exist | `ruff check <existing paths>` non-zero | **Not** gated on `pyproject.toml` / `requirements.txt` / `setup.py`. Remove the old marker-gated `ruff check .` so a marked consumer does not run ruff twice. |
| `bandit` | always, same path rule | `bandit` not on PATH; **or** no remaining paths after excluding `tests/` | `bandit -c bandit.yaml -r <paths>` non-zero | Whole-tree AST on product paths. Complements changed-file `secret-scan`. |
| `python-unittest` | top-level `tests/test*.py` and **not** (marker + pytest on PATH) | not emitted (current contract) | suite non-zero | Name and discovery rule stay. |
| `pytest` | marker **and** pytest on PATH **and** `tests/` | not emitted | pytest non-zero | pytest-wins characterization **must stay**. Do not “fix” it. |
| `coverage` | `mode` in `{pr, release}` **and** a test runner will/did run | `mode==fast`; **or** `coverage` not on PATH; **or** no test runner this call | `coverage report` non-zero (includes `--fail-under` once set) | See §4. Never emit on a tree with no tests. |

**`_python` control flow after this change** (load-bearing):

```
ruff_check()                          # independent of markers
bandit_check()                        # independent of markers

has_marker = pyproject.toml | requirements.txt | setup.py
has_top_level_unittest = tests/test*.py

if has_marker and pytest_on_PATH and tests/:
    run pytest                        # existing early return, but AFTER ruff+bandit
    if mode in {pr, release} and coverage_on_PATH:
        coverage was NOT wrapping pytest on this landing
        emit coverage skip "pytest runner owns tests; measure unittest trees only"
    return
if has_top_level_unittest:
    if mode in {pr, release} and coverage_on_PATH:
        coverage run --rcfile=.coveragerc -m unittest discover -s tests
        # this IS the python-unittest check (same name; fail if tests fail)
        then coverage report            # check name coverage
    else:
        python -m unittest discover -s tests
```

Rationale: ruff/bandit must not sit behind the pytest-wins `return`. Today they do. That is the bug this slice fixes for marked consumers *and* for this unmarked tree.

### 1.3 Consumer optional adapters (Bucket B) — skip-unless-signal

Do **not** enable on this repo. Detect tree signals the same way `_composer` / `_node` already work. No profile-JSON loader.

| Name | Signal (must exist) | Skip | Fail | Absent (do not emit) |
| --- | --- | --- | --- | --- |
| `semgrep` | any of `semgrep.yaml`, `.semgrep.yml`, `.semgrep.yaml`, or a non-empty `.semgrep/` directory | signal present **and** `semgrep` not on PATH | `semgrep scan --error --config <that file or .semgrep>` non-zero | no signal |
| `trivy-config` | any of `Dockerfile`, `dockerfile`, `Containerfile`, or `docker-compose*.yml` / `docker-compose*.yaml` at repo root | signal present **and** `trivy` not on PATH | `trivy config --exit-code 1 .` non-zero | no signal |
| `npm-lint` | already: root `package.json` script `lint` | already: no npm | `npm run lint` non-zero | no `lint` script |
| `npm-prettier` | root `package.json` script `prettier` | no npm | `npm run prettier` non-zero | no `prettier` script |
| `npm-format` | root `package.json` script `format` | no npm | `npm run format` non-zero | no `format` script |

Rules for B:

- **Never** `semgrep --config auto` (network rule pack). Use only the consumer’s own config path.
- **Never** `trivy image` on this landing (needs a built image / registry). Config scan is the Dockerfile signal.
- **Never** `npx eslint` / `npx prettier` without a package script (would download).
- This product tree has no `package.json`, no Dockerfile, no semgrep config → **zero** of these checks appear on a default `base` run.
- Missing binary + present signal = `skip`, not `fail`. Consumers are not required to have the tool.

### 1.4 Modes

| Mode | ruff / bandit | coverage | consumer B | unittest |
| --- | --- | --- | --- | --- |
| `fast` | run (skip if missing) | **skip** (emit `coverage` skip *or* omit; either is fine if tests still run) | same skip-unless-signal | run |
| `pr` | run | gate if tool + fail-under set | same | run (wrapped when coverage present) |
| `release` | same as `pr` | same as `pr` | same | same |

CI uses `--mode pr`.

---

## 2. `ruff.toml` location and selected rules

**Location:** repo root `ruff.toml`. Not `pyproject.toml`. `ruff.toml` does **not** flip `detect_repo`.

**Command:** `ruff check <existing QUALITY_PY_PATHS>` (not `ruff check .`, which would wander into `engineering/` and examples).

**Conservative first select** so the current tree can pass without an isort/line-length rewrite:

```toml
target-version = "py310"
line-length = 120

exclude = [
  ".git",
  ".grok-stack/runtime",
  "dist",
  "packages",
  "engineering",
  "examples",
  "__pycache__",
]

[lint]
select = ["E4", "E7", "E9", "F"]
ignore = ["E402"]
```

| Choice | Why |
| --- | --- |
| `E4` `E7` `E9` `F` | Real errors + pyflakes. Unused import (`F401`) still fails (required by task_analyst P0). |
| No full `E` | `E501` would force a line-length sweep. Out of vertical. |
| No `I` (isort) | `scripts/` and `tests/` insert `sys.path` then import `adaptive_grok`. isort would churn every file. Later slice. |
| `ignore = ["E402"]` | Same path-insert pattern. Structural, not debt. |
| `target-version = "py310"` | Matches toolchain minimum. |

**What the writer does after adding the file:**

1. Run `ruff check` on the path set.
2. If the tree is clean → ship that config.
3. If there are a handful of `F401` / `F841` / `F541` → fix those (allowed application edits in this vertical).
4. If there are more than ~15 findings that are style-only → add the **minimum** extra `ignore` and list each code in the change package. Do not `ruff check --fix` the whole tree as a format rewrite.
5. Do **not** add `ruff format` as a fail-closed check in 2.0.6.

I did not execute ruff (no shell on this agent). The writer must run it once and record the result under `evidence/ruff-first-run.md` (exit code + finding count). Empty file if clean.

---

## 3. Bandit config / excludes

**File:** `bandit.yaml` at repo root (YAML is unambiguous; `.bandit` INI varies by version).

```yaml
exclude_dirs:
  - tests
  - engineering
  - dist
  - packages
  - examples
  - .grok-stack/runtime
skips:
  - B101   # assert_used (tests excluded anyway; keep for any leftover)
  - B404   # import_subprocess — this product is a CLI runner
  - B603   # subprocess without shell=True is the *safe* pattern
  - B607   # start process with a PATH name (git, python, ruff, …)
```

**Command:** `bandit -c bandit.yaml -q -r <existing QUALITY_PY_PATHS minus tests>`  
If only `tests/` would have been scanned, emit `bandit` `skip` `no non-test python paths`.

**Still on (must fail if introduced):** `B602` (`shell=True`), `B307` (`eval`), `B324` (weak hash), `B105` (hardcoded password), SQL concat. Current tree has **no** `shell=True` / `eval(` / `hashlib.md5` in product Python (grep 2026-08-16). Expect a clean first run; if Bandit reports a real finding, **fix it**, do not broaden skips.

Bandit excludes `tests/` and `engineering/` as required. Planted `eval` in `tests/` must **not** fail `bandit`; planted `eval` under `.grok-stack/adaptive_grok/` must.

---

## 4. Coverage: measure this session, then gate

**Do not invent 90%.** Baseline is currently unknown. This agent cannot run the suite.

### 4.1 Measure (writer, this session, before enabling fail-under)

```bash
python3 -m pip install --user 'coverage>=7,<8'
python3 -m coverage run --rcfile=.coveragerc -m unittest discover -s tests
python3 -m coverage report
```

Write `engineering/changes/20260816-ship-working-v2-0-6-quality-contour-ec0388/evidence/coverage-baseline.md` with:

- date / coverage version
- exact command
- TOTAL line % and branch %
- chosen `fail_under` = `max(0, floor(line_percent) - 2)`
- one sentence: this is a ratchet, not a handbook 90

### 4.2 Config (land first **without** `fail_under`, then add the measured number)

`.coveragerc`:

```ini
[run]
branch = True
source =
    .grok-stack/adaptive_grok
    scripts
omit =
    tests/*
    */__pycache__/*
    .grok-stack/runtime/*
    engineering/*

[report]
skip_empty = True
show_missing = True
# fail_under = <paste measured-2 after evidence/coverage-baseline.md exists>
```

Do **not** put `fail_under` in the file until the baseline note exists. If `coverage` cannot be installed in this session, ship the runner + report-only check (no `fail_under`) and leave the baseline file saying “ungated; measure on CI/next session”. CI will then install coverage and the writer must come back with a number before calling the contour complete — **do not guess**.

Once the number is written: set `[report] fail_under = <N>` in `.coveragerc` only. Do not also hard-code N in Python.

### 4.3 How the check runs (no third suite)

- Inside `verify()` `pr`/`release`: wrap unittest with `coverage run` (that run **is** `python-unittest`), then `coverage report` (`coverage`).
- CI keep **one** extra fail-fast `python -m unittest discover -s tests` **or** drop it. Do **not** keep fail-fast unittest **and** an unwrapped unittest inside verify **and** a coverage run (three). Target: **two** suite executions max, same as today.
- `fast`: unwrapped unittest; `coverage` skip.
- Marker+pytest consumers: do not wrap pytest on this landing; `coverage` skip with an honest reason.
- No Codecov, no upload, no badge.

`.gitignore`: add `.coverage`, `.coverage.*`, `htmlcov/`, `.ruff_cache/`.  
`manifest.py` already excludes `.coverage`. Add `htmlcov` / `.ruff_cache` to `EXCLUDED_PARTS` if they would otherwise pack.

---

## 5. Consumer optional checks — signal table

This repo today: no root `package.json`, no Dockerfile, no `semgrep.yaml` / `.semgrep/`. Adapters must be invisible here.

| Adapter | Detect | Tool | Command | This repo |
| --- | --- | --- | --- | --- |
| Semgrep | `semgrep.yaml` \| `.semgrep.yml` \| `.semgrep.yaml` \| non-empty `.semgrep/` | `semgrep` on PATH | `semgrep scan --error --config <detected>` | not emitted |
| Trivy | `Dockerfile` \| `dockerfile` \| `Containerfile` \| root `docker-compose*.yml(l)` | `trivy` on PATH | `trivy config --exit-code 1 .` | not emitted |
| ESLint | existing `_node`: script `lint` | `npm` | `npm run lint` → check `npm-lint` | not emitted |
| Prettier | new: script `prettier` and/or `format` | `npm` | `npm run prettier` / `npm run format` | not emitted |

Extend `_node` names:

```
lint, typecheck, test
+ prettier if script exists
+ format if script exists
+ build if mode in {pr, release}   # existing
```

PHPStan / PHPCS / `npm-lint` stay as they are.

---

## 6. CI workflow

Edit **both** files with identical bytes (locked by `tests/test_deploy.py::test_root_workflow_equals_template`):

- `.github/workflows/adaptive-grok.yml`
- `.grok-stack/templates/ci/github-actions.yml`

```yaml
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Quality tools
        run: python -m pip install 'ruff>=0.6,<1' 'bandit>=1.7,<2' 'coverage>=7,<8'
      - name: Unit tests
        run: python -m unittest discover -s tests
      - name: Doctor
        run: python scripts/grok_doctor.py
      - name: Verify
        run: python scripts/grok_verify.py --mode pr
```

Pins live in the workflow, **not** in `requirements.txt`. That is not a packaging marker and does not flip `detect_repo`.

Keep: conditional `package` job, `upload-artifact`, **no** `gh release` / `git push` / `docker push`.

Update `tests/test_deploy.py` to assert the workflow contains `pip install` + `ruff` + `bandit` + `coverage` and still has no publish verbs.

**Dependabot** (A4, same vertical): `.github/dependabot.yml`

```yaml
version: 2
updates:
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
```

No `pip` ecosystem.

**Do not** add ruff/bandit/coverage to `.grok-stack/config/toolchain.json`. `install_into.py` must not start offering them. They are CI/dev host tools.

---

## 7. VERSION / CHANGELOG / README / package zip

Identity bump is part of “working 2.0.6”. Publish is not.

| File | Action |
| --- | --- |
| `VERSION` | `2.0.6` |
| `README.md` H1 | `Adaptive Grok Build Pro v2.0.6` |
| `CHANGELOG.md` | new top `## 2.0.6 — 2026-08-16`; **do not rewrite** 2.0.5 or older |
| `dist/RELEASE-NOTES.md` | replace with the 2.0.6 section (notes-file for a later human release) |
| `packages/README.md` | add 2.0.6 row; keep 2.0.0–2.0.5 |
| optional `engineering/runbooks/publish-v2.0.6.md` | print-only last mile, copy 2.0.5 pattern |

CHANGELOG 2.0.6 bullets (honest, short):

- `grok_verify` runs Ruff from `ruff.toml` without a packaging marker; local skip-if-missing; CI fail-closed
- Bandit AST next to regex `secret-scan`; excludes `tests/` and `engineering/`
- Coverage.py report in `pr`/`release` after a measured fail-under (cite the number once known)
- Dependabot for GitHub Actions only
- Optional consumer Semgrep / Trivy config / npm prettier|format when those signals exist; not enabled on this tree
- 2.0.5 remains the previous published GitHub Latest until a human last mile

Package assemble (writer **does** this; it is not publish):

```bash
python3 scripts/package_stack.py
cp dist/adaptive-grok-build-pro-v2.0.6.zip* packages/
```

Contracts to keep: zip name follows `VERSION`; prefix `adaptive-grok-build-pro/`; includes `MANIFEST.sha256`; excludes `.env`, keys, `err.log`, runtime state, `.coverage`. `make package` unchanged.

**Do not run:** `git tag`, `git push`, `gh release create`. Leave tag `v2.0.5` at `7c0ae7573535ddd0cfe3800f81278991ced81584` untouched.

---

## 8. Forbidden files and non-goals

Must **not** appear at repo root:

- `pyproject.toml`
- `requirements.txt`
- `setup.py`

Add a structure test: this product tree has none of those three. That locks the anti-pattern (`decisions.md` 2026-08-14: marker flips `detect_repo` and, with pytest on PATH, skips `python-unittest`).

Also out:

- rewriting `verify()` to honor `required_checks` / `optional_checks`
- `ruff format` fail-closed, pre-commit as a second source of truth
- `trivy image`, `semgrep --config auto`, pip-audit, Trivy fs as a product gate
- Bucket C (Sonar, Checkmarx, ZAP, k6-as-dependency, Datadog, ELK, Nagios, TestRail, ArchUnit, Jaeger, Codecov, Snyk-required, Sentry-in-the-CLI)
- new service / DB / paid SaaS
- making ruff/bandit/coverage **required** toolchain / `install_into` deps
- claiming “Dobryakov-complete” or “quality-scanner platform”
- 2.1.0

Quality-profile JSON **may** list new names as documentation only:

- `base.json` `optional_checks`: add `ruff`, `bandit`, `coverage`, `semgrep` (keep `contract-structure`, `sql-safety`)
- `frontend.json` `optional_checks`: add `npm-prettier`, `npm-format`
- `infra.json` `optional_checks`: add `trivy-config`

Schema already requires `schema_version`, `name == stem`, `required_checks` list. Do not add `ruff` to `required_checks` — that would lie until a later wiring slice.

---

## 9. Implementation sequence for `general_implementer`

Exactly one writer. Tests first. Smallest coherent land:

1. Characterization tests in `tests/test_verification_doctor.py` + `test_deploy.py` + `test_structure.py` (never `verify(ROOT)`). See task_analyst P0; honor them.
2. `ruff.toml` + `_ruff` independent of markers; delete marker-gated `ruff check .`.
3. `bandit.yaml` + `_bandit`.
4. `.coveragerc` without `fail_under` + wrap unittest in `pr`/`release`.
5. Measure → `evidence/coverage-baseline.md` → set `fail_under`.
6. `_semgrep` / `_trivy_config` / `_node` prettier|format (skip-unless-signal).
7. CI template + root workflow (byte-identical) + Dependabot.
8. Profile JSON honesty only.
9. `.gitignore` coverage/ruff caches.
10. `VERSION` 2.0.6 + CHANGELOG + README + RELEASE-NOTES + `packages/` zip.

Then: fill this change package’s stub `architecture.md` / `requirements.md` / `tasks.md` / `test-plan.md` from this report. Transition `ready` **before** the completion `grok_verify` / reviews (`decisions.md` 2026-08-14).

---

## 10. Tests the writer must add (failing first)

Reuse `project_copy`. Patch `command_exists` / `_command_check`. Keep existing unmarked-unittest and pytest-wins tests green.

| Test | Expected |
| --- | --- |
| unmarked tree + ruff absent | `ruff` is `skip`; `python-unittest` still present |
| unmarked tree + ruff present | `ruff` emitted **and** `python-unittest` emitted (no pytest-wins) |
| planted unused import under a quality path | `ruff` `fail`, overall `fail` |
| marker + pytest present | still `pytest`, no `python-unittest` (existing) |
| bandit absent | `bandit` `skip`; `secret-scan` still in `verify()` |
| planted `eval(` in product path + bandit present | `bandit` `fail` |
| planted `eval(` only in `tests/` | `bandit` does not fail because of it |
| secret-shaped assignment | `secret-scan` still `fail` with bandit present |
| coverage absent, mode `pr` | `coverage` `skip`; unittest ran |
| mode `fast` + coverage present | unittest ran; coverage not fail-closed |
| mode `pr` + coverage present + fail-under 100 on a tiny fixture | `coverage` `fail` |
| no semgrep config | no `semgrep` check |
| `semgrep.yaml` + no binary | `semgrep` `skip` |
| no Dockerfile | no `trivy-config` check |
| `Dockerfile` + no trivy | `trivy-config` `skip` |
| `package.json` script `prettier` | `npm-prettier` emitted when npm mocked present |
| ROOT has no `pyproject.toml` / `requirements.txt` / `setup.py` | structure test |
| workflow == template and contains pip install of the three tools | deploy test |
| workflow still has no `gh release` / `git push` / `docker push` | existing |

---

## 11. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Ruff red bar on current style | Conservative `select`; fix only F-errors; no isort/E501 sweep |
| Coverage flake from a guessed 90 | Measure, then `floor − 2`; ungated until the note exists |
| Triple unittest in CI | Wrap, do not stack |
| Profile JSON looks executable | Docs + CHANGELOG say it is still documentation |
| `secret-scan` still changed-files only | Bandit is the complementary whole-path AST; keep scopes honest |
| Consumer PHP repo with ruff installed | `ruff check` only existing quality paths (the installed stack). Should stay clean. |
| Assembled zip ≠ GitHub Latest | Intentional until human `grok_deploy` |

---

## Stop

Design is bounded. `general_implementer` owns the vertical above. Do not start a second writer. Do not publish.
