# Analysis — task_analyst

Change: `20260816-ship-working-v2-0-6-quality-contour-ec0388`  
Route: `ec0388060302` · intent=`feature` · risk=`low` · write=`general_implementer`  
Reviews after implementation: `code_reviewer` + `test_reviewer`  
Evidence kinds: `verification`, `code_review`, `test_review`  
Human gates on this route: none  
Narrow question: **What is the complete acceptance checklist for a working 2.0.6, and what is out of scope?**

Read-only. No application-code edits. No `.env`. No push / tag / merge / deploy.

---

## Ruling (one screen)

User prompt «всё полностью до рабочей версии 2.0.6 собирай» means **assemble a working 2.0.6 tree + zip**. It does **not** mean GitHub tag, `git push`, or `gh release create`.

- **In:** approved Bucket A on *this* repo (Ruff → Bandit → Coverage.py after a measured baseline → Dependabot `github-actions` only), identity bump `2.0.5` → `2.0.6`, deterministic zip under `dist/` copied to `packages/`.
- **Out:** Dobryakov handbook dump; `pyproject.toml` / `requirements.txt` / `setup.py`; retag or rebuild `v2.0.5`; Bucket C scanners/SaaS; last-mile publish.
- **Bucket B** (Semgrep / Trivy image / ESLint-Prettier) stays later and **optional for consumers**. If any adapter is added, it must **skip on this tree**.
- Prior design approval is [human-approval.md](../../20260816-release-readiness-gap-vs-dobryakov-code-quality-ef7b14/evidence/human-approval.md) (2026-08-16, «Ещё и профили для чужих репо»). That authorized A + later optional B. It did **not** authorize production publish.
- The cd8a96 «делай» exception applied only to finishing **already-built** `v2.0.5`. It does not transfer to 2.0.6.

Last mile remains `python3 scripts/grok_deploy.py`. Humans own the printed commands.

---

## Current facts (do not treat as done)

| Item | Today |
| --- | --- |
| `VERSION` | `2.0.5` |
| README H1 | `Adaptive Grok Build Pro v2.0.5` |
| CHANGELOG latest | `## 2.0.5 — 2026-08-15` |
| Published Latest | `v2.0.5` @ `7c0ae7573535ddd0cfe3800f81278991ced81584` (route `base_commit`) |
| Tracked zip | `packages/adaptive-grok-build-pro-v2.0.5.zip` |
| `ruff.toml` / `.bandit` / `.coveragerc` / `.github/dependabot.yml` | **Absent** |
| `pyproject.toml` / `requirements.txt` / `setup.py` | **Absent** (must stay that way) |
| `_python()` ruff | Only if a packaging marker exists **and** `ruff` is on PATH. Dead on this tree. |
| `python-unittest` | Runs when `tests/test*.py` exist and no packaging marker. Must keep working. |
| CI | unittest + doctor + `grok_verify --mode pr`. No `pip install ruff/bandit/coverage`. No publish job. |
| `verify()` vs profile JSON | `base.json` lists checks; `verify()` does **not** read those lists. Wiring `required_checks` is **not** A. |
| Semgrep / Trivy / ESLint in this product | **Absent.** Do not enable on this tree. |

`detect_repo` treats `pyproject.toml` or `requirements.txt` as `python:project`. `_python` with a marker + pytest on PATH **skips** `python-unittest` (`decisions.md` 2026-08-14). Lighting tools with a packaging marker is a regression.

---

## 1. Acceptance — working 2.0.6

A working 2.0.6 is the **A-land product + assembled package + consistent identity**. It is not “Latest on GitHub”.

### 1.1 Product (Bucket A on this repo)

Order is load-bearing: Ruff first, then Bandit, then Coverage after a measured baseline, then Dependabot.

- [ ] **Ruff is a first-class `grok_verify` check**, not gated on `pyproject.toml` / `requirements.txt` / `setup.py`.
- [ ] Ruff config is **`ruff.toml`**, not `pyproject.toml`. Paths: `.grok-stack/adaptive_grok`, `scripts/`, `tests/`, root hook shims.
- [ ] Local: if `ruff` is missing, the `ruff` check is **`skip`**, not `fail`.
- [ ] CI: `pip install ruff` (or equivalent, not a packaging marker) then the same `python scripts/grok_verify.py --mode pr` **fail-closes** on ruff.
- [ ] First landing uses a **narrow, passable** rule set (architect residual: `E`, `F`, `I` or equivalent). Autofix or suppress only real noise. Do not leave a red ruff bar on the ship tree.
- [ ] An unused import (or equivalent `F`/`E` violation) in those paths makes `ruff` **fail**.
- [ ] **Bandit** is a separate `grok_verify` check (AST). Config `.bandit` or `bandit.yaml`. Does **not** replace regex `secret-scan`.
- [ ] Local: missing `bandit` → **`skip`**. CI: install then fail-closed.
- [ ] **Coverage.py** is added only **after measuring** line (and, if used, branch) coverage on `.grok-stack/adaptive_grok` + `scripts`. **No guessed 90%.** No Codecov SaaS.
- [ ] Measured number is recorded (`.coveragerc` comment and/or CHANGELOG 2.0.6 / this change package). `--fail-under` is **measured − 2** or that documented floor.
- [ ] Coverage does **not** add a third suite run. Either wrap the existing `python-unittest` inside verify, or drop the extra CI `unittest discover` step so CI is doctor + `grok_verify --mode pr` (which already runs the suite).
- [ ] `fast` may skip the coverage fail-under gate. `pr` and `release` include it once landed.
- [ ] Local: missing `coverage` → **`skip`**. CI: install then fail-closed.
- [ ] **`.github/dependabot.yml`** exists with `package-ecosystem: github-actions` only (weekly). **No** `pip` ecosystem (no lockfile).
- [ ] `secret-scan`, `git-diff-check`, `contract-structure`, `sql-safety` still run. Bandit complements secrets; it does not delete them.
- [ ] Given this tree **without** a packaging marker and with `tests/test*.py`, `grok_verify --mode pr` still emits **`python-unittest`** and it still runs (`decisions.md` 2026-08-14).
- [ ] `detect_repo` on this product tree stays **`kind=generic`** (no `python:project` signal from a new marker).
- [ ] Runtime `adaptive_grok` stays **stdlib-only**. Ruff / Bandit / Coverage are host/CI commands, not imports and not required `toolchain.json` tools. `install_into.py` default / `--no-deps` must **not** start pulling them.
- [ ] `python scripts/grok_doctor.py` has **no fail** items on the ship tree.
- [ ] Profile JSON may *name* `ruff` / `bandit` / `coverage` under `optional_checks` (honest docs). **Do not** rewrite `verify()` to honor `required_checks` in this slice.
- [ ] 2.0.5 hook / routing / fail-open-after-pull behavior is unchanged.

### 1.2 Identity

- [ ] `VERSION` is exactly `2.0.6`.
- [ ] README H1 is `Adaptive Grok Build Pro v2.0.5` → **`Adaptive Grok Build Pro v2.0.6`**.
- [ ] CHANGELOG has a new top section `## 2.0.6` dated **2026-08-16** that states: Ruff without a packaging marker; Bandit next to `secret-scan`; measured coverage floor; Dependabot for Actions only; 2.0.5 remains the previous published release.
- [ ] Existing `## 2.0.5` (and older) text is **not rewritten**.
- [ ] `dist/RELEASE-NOTES.md` is the 2.0.6 CHANGELOG section (same pattern as 2.0.5).
- [ ] `packages/README.md` table gains a `2.0.6` row. `2.0.5` and older rows stay.
- [ ] Optional but consistent: `engineering/runbooks/publish-v2.0.6.md` **prints** last-mile commands. Agents do not execute them.
- [ ] No document claims “Dobryakov-complete”, “quality-scanner platform”, or “handbook dump shipped”.
- [ ] Tag `v2.0.5` and GitHub Release `v2.0.5` are **untouched** (no `-f`, no rebuild of the 2.0.5 zip).

### 1.3 Package (assemble)

- [ ] `python3 scripts/package_stack.py` writes `dist/adaptive-grok-build-pro-v2.0.6.zip` and sibling `.sha256`.
- [ ] Zip default path follows `VERSION` (`tests/test_manifest_package.py` contract).
- [ ] `cp dist/adaptive-grok-build-pro-v2.0.6.zip* packages/` so the tracked copy exists.
- [ ] Archive prefix remains `adaptive-grok-build-pro/…`, includes `MANIFEST.sha256`, excludes `.grok-stack/runtime` state (except `.gitkeep`), excludes `.env` / private keys.
- [ ] Zip is deterministic (fixed zip time already in `package_stack.py`).
- [ ] `make package` still aliases `package_stack.py`.

### 1.4 Last-mile GitHub tag / release (human-owned — **not** this prompt)

These boxes are **not** required to call 2.0.6 “assembled / working” on this route. They become the human (or a later explicitly-approved `grok_deploy`) step.

- [ ] Change package is `ready`; `python scripts/grok_verify.py --mode pr` and both review receipts are bound to the **final** fingerprint (transition `ready` **before** recording evidence — `decisions.md` 2026-08-14).
- [ ] Human runs `python3 scripts/grok_deploy.py` and then the printed commands:

```bash
python3 scripts/package_stack.py
cp dist/adaptive-grok-build-pro-v2.0.6.zip* packages/
git tag -a v2.0.6 -m "v2.0.6"
git push origin <branch>
git push origin v2.0.6
gh release create v2.0.6 packages/adaptive-grok-build-pro-v2.0.6.zip packages/adaptive-grok-build-pro-v2.0.6.zip.sha256 --notes-file dist/RELEASE-NOTES.md
```

- [ ] After that human step only: `gh release view --latest` is `tag_name: v2.0.6`; `v2.0.5` remains a previous release.

**This prompt does not authorize those git/gh lines.** See §4.

---

## 2. Non-goals

- Do **not** `git tag`, `git push`, `gh release create`, merge, or deploy from this agent session.
- Do **not** retag, rebuild, or force-push `v2.0.5`.
- Do **not** add `pyproject.toml`, `requirements.txt`, or `setup.py`.
- Do **not** dump the Dobryakov 57-tool handbook into the tree or docs.
- Do **not** implement Bucket B as default-on this repo (Semgrep, Trivy image/fs as a product gate, ESLint/Prettier/Biome vendored here).
- Do **not** implement Bucket C: SonarQube, Checkmarx, Coverity, ZAP/Burp/Nessus, JMeter/k6 as a product dependency, Datadog/New Relic/Dynatrace, ELK/Splunk, Nagios/Zabbix, TestRail/Jira TMS, ArchUnit/NDepend, Jaeger, Codecov SaaS, Snyk-as-required, Sentry-in-the-CLI.
- Do **not** add a new service, database, queue, framework, or paid SaaS.
- Do **not** make `verify()` honor quality-profile `required_checks` (later slice).
- Do **not** add Dependabot `pip` (no lockfile). Optional `requirements-ci.txt` is allowed **only** if it is not named `requirements.txt` and does not flip `detect_repo` / `_python` `has_project`.
- Do **not** add ruff/bandit/coverage as **required** toolchain tools; consumer installs stay python3+git.
- Do **not** force pre-commit as a second source of truth.
- Do **not** claim the product is a quality-scanner platform.
- Do **not** change Bitrix core or expand Bitrix adapters unless a consumer signal requires it (this route is `generic`).
- Do **not** open 2.1.0.

---

## 3. Test requirements (failing test first)

Add characterization / failing tests **before** wiring checks. Prefer `tests/test_verification_doctor.py` + `project_copy` (never `verify(ROOT)` from inside the suite — that recurses). Keep existing unmarked-tree unittest tests green.

### P0 — Ruff without a packaging marker still runs unittest

- [ ] Given a `project_copy` with `tests/test*.py` and **no** `pyproject.toml` / `requirements.txt` / `setup.py`, when `verify` runs, then a `python-unittest` check exists (pass on `_PASSING_UNITTEST`, fail on `_FAILING_UNITTEST`).
- [ ] Same tree: when `ruff` is **absent**, a `ruff` check is `skip` or omitted without failing the run for that reason; `python-unittest` still ran.
- [ ] Same tree: when `ruff` is **present** (patch `command_exists` / `_command_check`), a `ruff` check is emitted **and** `python-unittest` is still emitted. Marker-less + ruff-on-PATH must not take the pytest-wins early return.
- [ ] Given a planted unused import (or `ruff` non-zero), `ruff` is `fail` and overall verify is `fail`.
- [ ] Given a packaging marker **and** pytest on PATH, existing contract remains: `pytest` runs, `python-unittest` does **not** (do not “fix” pytest-wins as a side quest).
- [ ] This product tree itself has **no** packaging marker after the change.

### P0 — Bandit

- [ ] Missing `bandit` → `bandit` is `skip`, not `fail`; `secret-scan` still present.
- [ ] Present `bandit` → a `bandit` check is emitted; a planted AST issue (e.g. `subprocess` with `shell=True` or `eval`) fails `bandit`.
- [ ] A secret-shaped assignment still fails `secret-scan` even when Bandit is present (complement, not replacement).

### P0 — Coverage baseline

- [ ] First commit/test records the **measured** number; the fail-under is not a guessed 90.
- [ ] `pr`/`release`: coverage below the documented floor fails the coverage check.
- [ ] `fast`: coverage fail-under may skip; unittest still runs.
- [ ] Missing `coverage` locally → `skip`, not `fail`.
- [ ] Suite is not executed three times in CI.

### P0 — Consumer optional checks skip on this tree

- [ ] Semgrep / Trivy / ESLint (if any adapter exists) are **not** fail-closed on this repo: no `package.json` at root, no Dockerfile, no consumer Semgrep config. Checks are absent or `skip`.
- [ ] This tree’s default `base` verify run does **not** require those binaries.
- [ ] If the writer adds skip-stubs for B, a `project_copy` **without** JS/Docker/semgrep config must not grow a failing `semgrep` / `trivy` / `eslint` check.

### P1 — Identity / package / doctor

- [ ] `package_stack._default_output` follows the new `VERSION`.
- [ ] Doctor still has no failures (`tests/test_verification_doctor.py`).
- [ ] README remains MIT / free / public / commercial / no EULA / no paid tier (`tests/test_structure.py`).
- [ ] `prepare_deploy` dry-run still prints tag/push/`gh release create` for whatever `VERSION` is; this change does **not** execute them.

### Verification after implementation

```bash
python scripts/grok_verify.py --mode pr
```

Then independent `code_review` + `test_review` on the **final** tree. A failing check returns to `general_implementer`.

---

## 4. Does this prompt authorize `git tag` / `gh release`?

**No.**

| Phrase | Meaning here |
| --- | --- |
| «собирай» | Assemble the working tree + zip (`package_stack` + `packages/` copy + identity). |
| «push» / «релиз» / «tag» / «делай» after a last-mile plan | Would be required to treat this as publish. **Not present.** |
| Adaptive-delivery close | “Do not deploy, publish, merge, or perform external writes as part of closure. The last mile is `python3 scripts/grok_deploy.py`; humans own the printed commands.” |
| Route `human_gates` | `[]` — no `production_action_approval`. |
| Prior cd8a96 «делай» | Finished **v2.0.5** only. Not reusable for 2.0.6. |
| Prior ef7b14 approval | Design for A + later optional B. Explicitly “not for implementation or production publish” on that route; implementation moved here. Still not publish. |

**Assemble 2.0.6. Last mile remains `grok_deploy`.** Do not run:

- `git tag -a v2.0.6`
- `git push origin …`
- `gh release create v2.0.6 …`

A later user prompt that names push/release, plus `grok_approve.py production` and a ready change, is the only way those commands become in-scope.

---

## Constraints that survive into implementation

1. No `pyproject.toml` / `requirements.txt` / `setup.py`.
2. `verify()` remains the source of truth; CI must not invent a parallel quality bar.
3. Ruff → Bandit → measured Coverage → Actions Dependabot.
4. Local skip-if-missing; CI install + fail-closed for A tools.
5. Stdlib-only runtime; no new service / DB / paid SaaS.
6. Do not retag 2.0.5.
7. Do not dump the handbook.
8. Bind receipts after the last change-package write (`ready` first).
9. Exactly one write owner: `general_implementer`.

---

## Residual risks (for architect / writer)

- Enabling Ruff fail-closed will hit current style debt until autofix or a narrow `select`.
- Coverage without a measured baseline will flake. Measure, then pin.
- Profile JSON stays decorative; docs must not claim `base.required_checks` now drives `verify()`.
- `secret-scan` still sees only `changed_files`. Bandit on the Python paths is the complementary whole-tree AST layer — keep the scopes honest.
- Assembling `packages/v2.0.6.zip` on `main` does not make GitHub Latest 2.0.6. That gap is **intentional** until a human last mile.

---

## Stop

Acceptance, non-goals, test-first requirements, and publish authorization are recorded. Implementation is in scope for `general_implementer` on this route after the analysis wave. Tag / GitHub Release are **not**.
