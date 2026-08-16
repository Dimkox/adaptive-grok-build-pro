# Docs research — versioning, packaging, verify contracts for 2.0.6

Route: `ec0388060302`. Change: `20260816-ship-working-v2-0-6-quality-contour-ec0388`.
Question: what versioning, packaging, and verify contracts must 2.0.6 keep, and what prior decisions forbid `pyproject.toml`?

Read-only. No application-code edits. No `.env`. No push / merge / deploy. No APIs invented.

## Sources

- `VERSION`, `CHANGELOG.md`, `README.md`, `QUICKSTART.md`, `AGENTS.md`, `Makefile`
- `engineering/decisions.md`, `engineering/mistakes.md`, `engineering/adr/` (empty)
- `engineering/runbooks/publish-v2.0.4.md`, `engineering/runbooks/publish-v2.0.5.md`
- `packages/README.md`, `.grok-stack/config/quality-profiles/base.json` (+ sibling profiles)
- `.grok/skills/adaptive-delivery/SKILL.md`, `.grok/skills/feature-workflow/SKILL.md`
- This change package (still a stub) and prior packages `2eacdf`, `aea9d4`, `58e51e`, `99b743`, `cd8a96`, `ef7b14`
- Tests: `tests/test_verification_doctor.py`, `tests/test_repo_router.py`, `tests/test_manifest_package.py`, `tests/test_deploy.py`, `tests/test_change_receipts.py`, `tests/test_structure.py`
- Implementation cross-check only to name already-shipped contracts: `verification.py` `_python`, `repo.py` `detect_repo`, `package_stack.py`, `manifest.py`, `deploy.py`, `.github/workflows/adaptive-grok.yml`

`engineering/contracts/{openapi,asyncapi,schemas}/` have no product APIs. `engineering/adr/` has no files.

This change package (`brief.md`, `requirements.md`, `architecture.md`, `state.json`) is still a stub (`status: draft`). Constraints below come from standing docs and prior approved packages, not from this package’s empty acceptance list.

---

## 0. Current identity (do not rewrite 2.0.5)

`VERSION` is still `2.0.5`. README H1 is `Adaptive Grok Build Pro v2.0.5`. Latest published artifacts are `packages/adaptive-grok-build-pro-v2.0.5.zip` + sibling `.sha256`. There is no `2.0.6` section in `CHANGELOG.md` and no `packages/adaptive-grok-build-pro-v2.0.6.zip`.

`cd8a96/requirements.md`:

> `git rev-parse 'v2.0.5^{}'` is `7c0ae7573535ddd0cfe3800f81278991ced81584`.
> Tag `v2.0.4` and Release `v2.0.4` are untouched.
> Tag no longer peels to `7c0ae75` → stop. Do not retag with `-f`.

`ef7b14` human approval + architecture:

> Do not retag v2.0.5. A-land is a new versioned change.
> No new service, DB, or paid SaaS.

So 2.0.6, if shipped, is a **new** `VERSION` / tag / zip / CHANGELOG section. It must leave the existing `v2.0.5` tag and GitHub Release alone.

---

## 1. Versioning contracts 2.0.6 must keep

### 1.1 `VERSION` is the source of truth

`CHANGELOG.md` 2.0.1:

> Version source of truth is `VERSION`; packager default output follows it

`scripts/package_stack.py` `_default_output`:

> `version = (root / 'VERSION').read_text(...).strip() or '0.0.0'`
> `return f'dist/adaptive-grok-build-pro-v{version}.zip'`

`tests/test_manifest_package.py::test_default_output_follows_version_file` locks that equality against the live `VERSION` file.

`58e51e/requirements.md` (first VERSION/packager contract):

> `VERSION` is `2.0.1`
> Packager default output is `dist/adaptive-grok-build-pro-v2.0.1.zip`

For 2.0.6 that same contract means: bump `VERSION` to `2.0.6` **before** packaging; do not hard-code a zip name.

### 1.2 User-facing strings must match `VERSION`

Standing pattern from shipped releases:

| Surface | Current | 2.0.6 must become |
| --- | --- | --- |
| `VERSION` | `2.0.5` | `2.0.6` |
| README H1 | `Adaptive Grok Build Pro v2.0.5` | same form with `v2.0.6` |
| `CHANGELOG.md` | top section `## 2.0.5 — 2026-08-15` | new top section `## 2.0.6 — …`; keep 2.0.5–2.0.0 history |
| `dist/RELEASE-NOTES.md` | 2.0.5 notes | 2.0.6 notes for `gh release create --notes-file` |
| `packages/README.md` table | last row 2.0.5 | add 2.0.6 row; do not drop prior rows |
| Tag | `v2.0.5` | new annotated `v2.0.6` (human-owned) |

`2eacdf` already used this pattern: “README H1 → v2.0.4; … one 2.0.4 changelog bullet.”

### 1.3 Last mile is human-owned; agents do not tag/push/release

`AGENTS.md` prohibited routine actions:

> Direct push to a protected/shared branch.
> Merge, publish, deploy, or production mutation by Grok Build without short-lived explicit approval.

`adaptive-delivery` §7:

> Do not deploy, publish, merge, or perform external writes as part of closure. Those are separate, explicitly approved actions. The last mile is `python3 scripts/grok_deploy.py`; humans own the printed commands.

`publish-v2.0.5.md`:

> Agents must not run `git push`, `git tag`, or `gh release`; humans own those commands.

`publish-v2.0.4.md` same agent rule, plus the check sequence 2.0.6 must still print:

1. `python3 scripts/grok_status.py` — change `ready`, evidence gaps empty
2. `make verify` / `python3 scripts/grok_verify.py --mode pr`
3. `python3 scripts/grok_deploy.py` dry-run
4. Human: `python3 scripts/grok_approve.py production --reason "…"`
5. Optional: `python3 scripts/grok_deploy.py --record` → receipt `deploy`/`prepared`

Printed command shape (from `deploy.py` `_human_commands` and `test_deploy.py::test_dry_run_ready_is_ok_without_receipt`):

```text
python3 scripts/package_stack.py
cp dist/adaptive-grok-build-pro-v{VERSION}.zip* packages/
git tag -a v{VERSION} -m "v{VERSION}"
git push origin {branch}
git push origin v{VERSION}
gh release create v{VERSION} packages/adaptive-grok-build-pro-v{VERSION}.zip packages/adaptive-grok-build-pro-v{VERSION}.zip.sha256 --notes-file dist/RELEASE-NOTES.md
```

`99b743` architecture:

> `scripts/grok_deploy.py` is prepare-only. … Never subprocess `git push`, `gh pr merge`, `gh release create`, `docker push`, `npm publish`.
> `packages/` is not updated as “published” until the later human gate.

`tests/test_deploy.py::test_prepare_sources_do_not_execute_publish_commands` locks that `deploy.py` / `grok_deploy.py` contain no `subprocess` / `os.system`.

`--record` still requires production approval (`test_record_without_approval_is_not_ok`). Dry-run does not write a `deploy` receipt.

### 1.4 Receipts after the last tree write

`decisions.md` 2026-08-14:

> Bind receipts after the last change-package write
> Transition the durable package to `ready` first, then run `grok_verify` and `grok_review`. Recording evidence before that last write guarantees stale receipts and a second verification loop.

`AGENTS.md` verification:

> Use the exact evidence kind requested by the route. A receipt is stale after any repository change.

This route requires `verification`, `code_review`, `test_review`. Adaptive-delivery §5–6: run `python scripts/grok_verify.py --mode pr`, then the listed review agents, then `python scripts/grok_review.py <kind> --status pass --report <path>`.

`mistakes.md` 2026-08-14: binding verify mid-implementation is the recorded failure mode.

---

## 2. Packaging contracts 2.0.6 must keep

### 2.1 Scratch vs tracked copies

`packages/README.md`:

> Tracked copies of published artifacts. Scratch rebuilds go to `dist/` (gitignored).
>
> ```bash
> python3 scripts/package_stack.py
> cp dist/adaptive-grok-build-pro-v$(tr -d '[:space:]' < VERSION).zip* packages/
> ```
>
> `.env` and private keys are never packaged.

`.gitignore` has `dist/`. `CHANGELOG.md` 2.0.2:

> Versioned zips and checksums are tracked under `packages/`
> GitHub Release `v2.0.2` ships zip, sha256, and source tar.gz

`CHANGELOG.md` 2.0.1: ready-to-publish zip lives at `dist/adaptive-grok-build-pro-v2.0.1.zip` (scratch). Humans copy into `packages/` at publish time.

`CHANGELOG.md` 2.0.0:

> Packaging excludes `.env`, `.env.*`, and private-key files from the zip/manifest

README Package:

> Default output is `dist/adaptive-grok-build-pro-v<VERSION>.zip` (gitignored scratch).
> Published copies live in `packages/` and on the GitHub Release. Zip members use the prefix `adaptive-grok-build-pro/`.

### 2.2 Archive membership and determinism (locked by tests)

`tests/test_manifest_package.py`:

| Test | Locked contract |
| --- | --- |
| `test_default_output_follows_version_file` | output path is `dist/adaptive-grok-build-pro-v{VERSION}.zip` |
| `test_archive_is_deterministic_and_self_verifying` | two builds byte-identical; members prefixed `adaptive-grok-build-pro/`; includes `MANIFEST.sha256`; executable bit preserved |
| `test_archive_excludes_dotenv_and_keys` | `.env`, `.env.local`, `*.pem` absent |
| `test_archive_excludes_err_log` | `err.log` absent |
| `test_project_archive_excludes_generated_artifacts` | `*.zip`, `__pycache__` absent |
| `test_runtime_state_is_not_packaged` | `.grok-stack/runtime/.gitkeep` kept; `active-route.json` not |

`manifest.py` `included_files` also excludes `.git`, `dist`, `.venv`, `vendor`, `node_modules`, `MANIFEST.sha256` (re-added after generate), `.coverage`, `*.pyc`/`*.pyo`/`*.zip`/`*.sha256`, and `.grok-stack/runtime/**` except `.gitkeep`. Secret suffixes: `.pem`, `.key`, `.p12`, `.pfx`. `.env` / `.env.*` except `.env.example`.

2.0.6 must not start packaging secrets, runtime state, or `dist/` scratch. Adding a coverage file later stays excluded (`.coverage` is already in `EXCLUDED_FILES`).

### 2.3 CI may package; CI must not publish

`CHANGELOG.md` 2.0.4:

> This-repo GitHub Actions: verify plus a conditional package job (no publish)

`.grok-stack/templates/ci/README.md`:

> This repository copies it to `.github/workflows/adaptive-grok.yml` (verify + conditional package; no publish).
> Local `make verify` is the source of truth. Hosted CI is optional and does not publish.

`99b743` decision 4:

> CI: copy template to `.github/workflows/adaptive-grok.yml`. Add a conditional `package` job (`if: hashFiles('scripts/package_stack.py')`). No publish job.

`tests/test_deploy.py`:

- `test_root_workflow_equals_template` — `.github/workflows/adaptive-grok.yml` bytes == template
- `test_template_package_job_is_conditional_and_has_no_publish` — workflow contains `hashFiles('scripts/package_stack.py')` and does **not** contain `gh release`, `docker push`, or `git push`

Current workflow jobs: `verify` (`unittest discover` + `grok_doctor` + `grok_verify --mode pr`) then conditional `package` (`package_stack.py` + `upload-artifact` of `dist/*.zip*`). Python 3.12. No publish.

2.0.6 may add CI install steps (the approved Ruff slice says `pip install ruff` then fail-closed) but must keep the no-publish job and the template-equals-root-workflow lock.

### 2.4 No new packaging marker or runtime dependency graph

`feature-workflow`:

> A new service, queue, datastore, framework, or major dependency requires an ADR and named approval.

`AGENTS.md`:

> Do not introduce a service, database, queue, framework, or dependency without explicit architectural justification.

`ad4090` code-review (still standing for this tree):

> No new service, queue, datastore, framework, `pyproject.toml`, `requirements.txt`, or third-party import.

`toolchain.json` pins host CLIs (python3, git, grok, optional gh/node/npm/php/composer). It does **not** list ruff, bandit, coverage, or pip packages. `install_into.py` required tools stay python3+git (`ef7b14` security-review: do not pull Ruff/Bandit via `install_into.py`).

Stdlib-only runtime stays stdlib-only (`ef7b14` brief: “Stdlib-only runtime stays stdlib-only”).

---

## 3. Verify contracts 2.0.6 must keep

### 3.1 Command and profile

`AGENTS.md` verification:

```bash
python scripts/grok_verify.py --mode pr
```

`Makefile`: `verify` → `python3 scripts/grok_verify.py --mode pr`. README: local checks `make doctor` / `make verify`. QUICKSTART step 6 is the same command.

This route `quality_profiles: ["base"]`. `base.json`:

```json
"required_checks": ["git-diff-check", "secret-scan"],
"optional_checks": ["contract-structure", "sql-safety"]
```

`ef7b14/architecture.md` honesty gap (do not “fix” as a side quest in A1):

> `quality-profiles/*.json` lists checks; `verification.py` does not read those lists.
> Quality-profile JSON is currently documentation; wiring `required_checks` is a separate later slice, not A1.
> `verify()` is the source of truth. Actions run the same command, not a parallel bar.

So 2.0.6 must not silently treat `base.json` as the execution list. `verify()` **always** runs `git-diff-check`, `secret-scan`, `contract-structure`, `sql-safety`, then `_python()`. PHP/Bitrix/Node adapters stay signal-gated. `python-unittest` is **not** in `base.json`; it still runs on this tree because `_python` sees `tests/test*.py`.

None of the quality-profile JSON files name `ruff` or `python-unittest`. Adding a first-class Ruff check is a `verification.py` / CI change, not a `base.json` rename, unless a later approved slice wires profiles.

### 3.2 `_python` control flow (must keep)

`2eacdf/architecture.md`:

```
has_marker = pyproject.toml | requirements.txt | setup.py
if has_marker:
    ruff if present
    if pytest present and tests/ exists:
        run pytest
        return  # no unittest
if tests/ has test*.py:
    run python-unittest
```

`decisions.md` 2026-08-14 — **Run unittest from verify without a packaging marker**:

> `verification._python` used `pyproject.toml` / `requirements.txt` / `setup.py` as the only trigger, so this repo’s `tests/` never ran under `grok_verify`. Detect `tests/test*.py` and run `python -m unittest discover -s tests`. Do not add a packaging marker just to light the check — that flips `detect_repo` and, when pytest is present, skips unittest.

`CHANGELOG.md` 2.0.4:

> `grok_verify` runs `python-unittest` when `tests/test*.py` exist, even without `pyproject.toml` / `requirements.txt` / `setup.py`
> `_python` unittest discovery matches top-level `tests/test*.py` (not nested rglob); pytest-wins is characterized

`2eacdf/requirements.md` acceptance 2.0.6 must not regress:

- repo with `tests/test_ok.py` and **no** packaging marker → check `python-unittest` exists and `pass`
- failing `tests/test_fail.py` and no marker → overall `fail` and `python-unittest` `fail`
- no `tests/test*.py` → no `python-unittest` check
- marker + pytest available → `pytest` runs, `python-unittest` does **not**
- contour tests use `project_copy` only; never `verify(ROOT)`
- check name stays `python-unittest`
- unittest timeout stays in the existing 900s budget

`2eacdf` “What does not change”: `stop_gate.py`, production invocation matcher, rematch / child-skip, HIGH_RISK list, Bitrix/secret/destructive/MCP gates, installer, packaging, VERSION — those were later versioned separately; 2.0.6 still must not casually rewrite them.

### 3.3 `detect_repo` language detection (must keep)

`repo.py`:

```python
if (root / 'pyproject.toml').is_file() or (root / 'requirements.txt').is_file():
    languages.append('python')
    signals.append('python:project')
```

This product tree has neither file, so `detect_repo` is `kind=generic`, `languages=[]` (see this route’s `active-route.json` `repo`). Adding `pyproject.toml` or `requirements.txt` flips the product repo to `kind=python`.

Note the slight implementation mismatch (already recorded, not invented): `detect_repo` does **not** look at `setup.py`; `_python` `has_project` does. Prior decisions treat all three as “packaging markers” and forbid adding any of them on this repo.

`tests/test_repo_router.py` locks `detect_repo` for **bitrix** (`kind=bitrix`) and **polyglot** (`composer.json` + `package.json` → php + typescript). There is **no** test that asserts this product tree stays `generic` or that a `pyproject.toml` flips `kind` to `python`. The flip is locked by implementation + `decisions.md`, not by a `detect_repo` unit test.

### 3.4 CI / doctor / contour still run unittest

`.github/workflows/adaptive-grok.yml` `verify` job:

```text
python -m unittest discover -s tests
python scripts/grok_doctor.py
python scripts/grok_verify.py --mode pr
```

`tests/test_change_receipts.py::ContourTests.test_contour_route_change_verify_review_has_no_evidence_gaps` requires a `python-unittest` pass inside `verify(mode='fast')` on a marker-less `project_copy`.

`tests/test_structure.py::test_quality_profiles_are_valid` requires every `quality-profiles/*.json` to have `schema_version: 1`, `name == stem`, and a `required_checks` list. 2.0.6 may add a profile file only if that schema holds.

`tests/test_structure.py` also locks MIT / free / public / no EULA / no paid tier on README.

### 3.5 Approved 2.0.6-class quality slice (from `ef7b14`, not yet implemented)

`ef7b14` was design-only (`write_agent: null`). Human `scope_and_design_approval` authorized a **later** write-owner route. That is this route’s job if 2.0.6 is “the working quality contour.”

Approved A order (`ef7b14/architecture.md`):

1. **Ruff first.** Config `ruff.toml` (not `pyproject.toml`). New `grok_verify` check, **not gated on packaging markers**. Local: skip if `ruff` missing. CI: `pip install ruff` then fail-closed. Paths: `.grok-stack/adaptive_grok`, `scripts/`, `tests/`, root hook shims.
2. Bandit second. Does not replace regex `secret-scan`.
3. Coverage.py third, only after measuring a baseline. No guessed 90%. No Codecov SaaS.
4. Dependabot only `.github/dependabot.yml` for `github-actions`. No pip ecosystem (no lockfile).

Bucket B (later, optional consumer profiles): Semgrep, Trivy image, ESLint/Prettier. Do **not** enable on this repo by default.

Bucket C (never on this product): SonarQube, Checkmarx, Coverity, ZAP/Burp/Nessus, JMeter/k6 as a product dependency, Datadog/New Relic/Dynatrace, ELK/Splunk, Nagios/Zabbix, TestRail/Jira TMS, ArchUnit/NDepend, Jaeger.

`ef7b14` architect ruling for a later «делай»:

> one write-owner route, one slice — **Ruff as a first-class `grok_verify` check without `pyproject.toml`.** Stop after that slice.

`ef7b14/requirements.md` non-goals of *that* route (implementation belongs here, still constrained):

> Do not claim the product is a quality-scanner platform.

So a working 2.0.6 quality contour, if it follows the approved design, is **A1 Ruff only**, plus the usual VERSION/CHANGELOG/package/docs bump. Bandit / coverage / Dependabot are later slices, not this land unless a new user-approved expansion is recorded.

---

## 4. What forbids `pyproject.toml`

This is a standing anti-pattern, not a suggestion.

### 4.1 Decision (highest in-tree ADR-equivalent; `engineering/adr/` is empty)

`engineering/decisions.md` 2026-08-14:

> Do not add a packaging marker just to light the check — that flips `detect_repo` and, when pytest is present, skips unittest.

### 4.2 Change-package architecture that closed the hollow-verify gap

`2eacdf/architecture.md`:

> Do not add `pyproject.toml` / `requirements.txt` / `setup.py` — those would flip `detect_repo` and currently *skip* this path.
> Keep ruff/pytest only when a Python-project marker exists. If pytest is invoked, skip unittest so the same suite is not run twice.

### 4.3 Quality-contour design + human approval (directly about Ruff)

`ef7b14/brief.md` constraints:

> Do not add `pyproject.toml` just to light Ruff (flips `detect_repo`, can skip unittest)

`ef7b14/architecture.md`:

> Adding `pyproject.toml` / `requirements.txt` / `setup.py` is forbidden as a Ruff trigger (`detect_repo` + pytest-wins).

`ef7b14/evidence/human-approval.md`:

> Do not add `pyproject.toml` to light Ruff.
> Do not retag v2.0.5.

`ef7b14` architect:

> **Do not add `pyproject.toml` to light Ruff.** That is a recorded anti-pattern (`decisions.md`: flips `detect_repo`, pytest-wins skips unittest).
> Design: dedicated check `ruff` … Config in **`ruff.toml`**, not `pyproject.toml`.

`ef7b14` security-review:

> **No `pyproject.toml`** — **Security-positive.** Adding a packaging marker flips `detect_repo` and, if pytest is on PATH, **skips** `python-unittest`. That would weaken the only behavioral gate this repo has. `ruff.toml` is the right config.

### 4.4 Why the flip is real (implementation, not a new API)

`verification.py` `_python`:

```python
has_project = any((root / item).exists() for item in ('pyproject.toml', 'requirements.txt', 'setup.py'))
...
if has_project:
    if command_exists('ruff'):
        results.append(_command_check(..., 'ruff', ['ruff', 'check', '.'], ...))
    if command_exists('pytest') and tests_dir.is_dir():
        results.append(_command_check(..., 'pytest', ['pytest', '-q'], ...))
        return results   # skips python-unittest
```

On a developer or CI image that happens to have `pytest` on PATH, adding `pyproject.toml` to “light Ruff” **drops this repo’s unittest gate**. That is the failure `test_python_pytest_wins_when_project_marker_present` characterizes.

`detect_repo` independently starts reporting `languages=['python']` / `kind='python'` if `pyproject.toml` or `requirements.txt` appears, changing routing signals for this product tree (today: `kind=generic`, `languages=[]`).

`CHANGELOG.md` 2.0.4 already advertises that unittest runs **without** those files. Adding them would contradict a shipped user-facing contract.

---

## 5. Tests that lock `detect_repo` / `_python` / ruff

### 5.1 `_python` (hard lock)

`tests/test_verification_doctor.py`:

| Test | Locked behavior |
| --- | --- |
| `test_python_runs_unittest_without_project_marker` | `project_copy` + `tests/test_ok.py`, **no** marker → `verify` has `python-unittest` `pass` |
| `test_python_unittest_failure_is_a_failed_check` | failing top-level test → overall `fail` and `python-unittest` `fail` |
| `test_python_skips_without_tests_or_project_marker` | no `tests/` → `_python(root) == []` |
| `test_python_ignores_non_python_tests_directory` | PHP-only `tests/` → `_python == []` |
| `test_python_ignores_nested_unittest_without_top_level` | `tests/nested/test_x.py` only → `_python == []` |
| `test_python_pytest_wins_when_project_marker_present` | writes a **consumer-fixture** `pyproject.toml` + mocks pytest present → results contain `pytest`, **not** `python-unittest` |

`aea9d4/test-plan.md` named the last two as residual-contradiction characterization. `2eacdf/requirements.md` named the first four as acceptance.

`tests/test_change_receipts.py::ContourTests` also requires `python-unittest` `pass` on a marker-less copy.

### 5.2 `detect_repo` (partial lock)

`tests/test_repo_router.py::RepoDetectionTests`:

- `test_detects_bitrix` — `bitrix/` + `local/modules/acme.demo` → `kind=bitrix`, domain `bitrix`, module `acme.demo`
- `test_detects_polyglot` — `composer.json` + `package.json` → `kind=polyglot`, languages include `php` and `typescript`

Other uses of `detect_repo` in that file are prompt-classification (`делай` is not a development prompt; `repair yourself` is). **No test asserts absence of `pyproject.toml` on ROOT, and no test asserts `kind=generic` for this product tree.**

### 5.3 Ruff (no lock yet)

`rg ruff tests/` returns **zero** matches. There is no test that:

- asserts this product tree has no `pyproject.toml` / `requirements.txt` / `setup.py`
- asserts ruff runs here without a packaging marker
- asserts ruff is skipped locally when the binary is missing
- asserts CI fail-closed after installing ruff
- asserts config is `ruff.toml` rather than `[tool.ruff]` in `pyproject.toml`

Today ruff only fires inside `_python` when a packaging marker exists **and** `ruff` is on PATH (`verification.py:186-188`). On this product tree that branch is dead. The approved 2.0.6 A1 slice is to add a **new** first-class check, not to flip the marker.

If 2.0.6 implements A1, new tests belong next to `test_verification_doctor.py` / CI characterization (`test_deploy.py` already owns the workflow-equals-template lock). They must not break the pytest-wins consumer fixture.

---

## 6. What 2.0.6 must not invent

No product OpenAPI/AsyncAPI/event schemas exist. Do not invent a publish API, a packaging-marker API, or a quality-profile execution API.

Do not treat `base.json` `required_checks` as executable until a later approved slice wires them.

Do not add `requirements.txt` or `setup.py` as a Ruff/pytest trigger (same anti-pattern as `pyproject.toml`).

Do not retag `v2.0.5`. Do not force-push. Do not have CI run `gh release` / `git push` / `docker push`.

Do not dump Dobryakov Bucket B/C, paid SaaS, or a new service/DB. Do not claim the product is a quality-scanner platform.

Do not run `git tag`, `git push`, or `gh release` as agent closure. Print via `grok_deploy.py`.

---

## 7. Implications for this write owner (facts, not a new design)

1. **Identity:** bump `VERSION` → `2.0.6` together with README H1, CHANGELOG top section, `dist/RELEASE-NOTES.md`, and a new `packages/` row. Leave 2.0.5 tag, zip, and GitHub Release untouched.
2. **Packaging:** `package_stack.py` output still follows `VERSION`; zip prefix `adaptive-grok-build-pro/`; exclude `.env`/keys/`err.log`/runtime; `packages/` copy is the human publish step. CI package job stays conditional and publish-free.
3. **Verify:** keep marker-less `python-unittest` on top-level `tests/test*.py`. Keep pytest-wins **only** for consumers that already have a marker. Do not add `pyproject.toml`.
4. **Approved quality increment:** first-class Ruff via `ruff.toml`, not gated on packaging markers; local skip-if-missing; CI `pip install ruff` fail-closed; paths `.grok-stack/adaptive_grok`, `scripts/`, `tests/`, root hook shims. Stop after that slice unless the user expands scope.
5. **Evidence:** transition change to `ready` **before** the completion `grok_verify` / reviews. This route needs `verification` + `code_review` + `test_review`.
6. **Missing tests today:** ruff behavior is undocumented by the suite; `_python` and packaging/VERSION/deploy tests are the regression fence 2.0.6 must keep green.

End of report.
