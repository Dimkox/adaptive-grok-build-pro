# Code review — self-scan leftover 2.0.6 product bugs

Change: `20260816-self-scan-and-fix-emerging-product-bugs-3c1039`  
Route: `3c10395cf76e` · reviewer: `code_reviewer` (read-only) · write owner: `general_implementer`  
Reviewed: 2026-08-16  
Subject: commit `11da31a3f3e60a0463233cb96c576da8517ddabd` (`Fix 2.0.6 leftovers: installer configs, deploy title, stale notes`)

**PASS.** I would not block.

I did not trust `evidence/implementation.md`. Compared local `HEAD` = `11da31a` to parent `e75f3a1` (GitHub raw of `origin/main`) plus the surrounding implementation, tests, and change-package contracts. This session has no shell, so there is no live `git show` / `unittest` / `ruff` / `bandit`. Equivalents are listed below.

---

## Verdict against the six required fixes

| # | Fix | Result |
| --- | --- | --- |
| 1 | CHANGELOG 2.0.6 lead does not say 2.0.5 is Latest | **PASS** |
| 2 | `install_into` copies `ruff.toml`, `bandit.yaml`, `.coveragerc` | **PASS** |
| 3 | `grok_deploy` prints `--title "Adaptive Grok Build Pro v<VERSION>"` | **PASS** |
| 4 | `__version__` matches `VERSION` | **PASS** |
| 5 | `package_stack` unlinks leftover root `MANIFEST.sha256` after zip | **PASS** |
| 6 | `AGENTS.md` Stop hook wording is warn-only | **PASS** |

Would I block? **No.**

---

## What was actually inspected

```text
# refs
read .git/HEAD                          → ref: refs/heads/main
read .git/refs/heads/main               → 11da31a3f3e60a0463233cb96c576da8517ddabd
read .git/refs/remotes/origin/main      → e75f3a1b92e247279fbb6210d46715a90cf7895c
read .git/COMMIT_EDITMSG                → Fix 2.0.6 leftovers: installer configs, deploy title, stale notes
read .git/logs/HEAD                     → e75f3a1 → 11da31a  commit: Fix 2.0.6 leftovers…
read .git/refs/tags/v2.0.6              → 8e7c5b67a1f9e51cc2f15586b72e0dceff7f8ee1
                                          (same annotated object as published v2.0.6; not retargeted)

# contracts
engineering/changes/…-3c1039/{brief,requirements,tasks,test-plan,architecture,release,rollback,state,route}.json/md
engineering/changes/…-3c1039/evidence/{analysis-repo_explorer,implementation}.md
.grok-stack/runtime/active-route.json   allowed_agents includes code_reviewer; write_agent=general_implementer

# parent (e75f3a1) via GitHub raw — the six bugs
CHANGELOG.md:5                          “2.0.5 remains … until a human last mile.”
scripts/install_into.py MANAGED_FILES   scripts + nine shims only
deploy.py:33                            gh release create … --notes-file (no --title)
.grok-stack/adaptive_grok/__init__.py   __version__ = "2.0.0"
scripts/package_stack.py write_archive  no unlink
AGENTS.md:99                            “The Stop hook blocks completion…”
.gitignore                              no MANIFEST.sha256
publish-v2.0.6.md:27                    no --title
tests/test_structure.py                 no changelog / __version__ tests

# HEAD (11da31a) product
CHANGELOG.md
scripts/install_into.py
.grok-stack/adaptive_grok/{deploy,__init__,doctor,manifest,repo}.py
scripts/package_stack.py
AGENTS.md
.gitignore
engineering/runbooks/publish-v2.0.6.md
VERSION  ruff.toml  bandit.yaml  .coveragerc
dist/RELEASE-NOTES.md                   gitignored scratch; cleaned to match CHANGELOG lead
packages/adaptive-grok-build-pro-v2.0.6.zip.sha256
stop_gate.py (root shim) + .grok/hooks/stop_gate.py
scripts/grok_deploy.py
README.md:131

# tests
tests/test_installer.py
tests/test_deploy.py
tests/test_structure.py
tests/test_manifest_package.py
tests/_support.py

# absences (read of each path → does not exist)
.github/                                (directory missing)
pyproject.toml  requirements.txt  setup.py
root MANIFEST.sha256
```

`origin/main` is still `e75f3a1`. Local `main` is `11da31a`. Tag `v2.0.6` is still annotated object `8e7c5b67`. No push, no retag. Matches “Stay 2.0.6. No GHA. No publish.”

---

## 1. CHANGELOG — PASS

Parent `CHANGELOG.md:5`:

```
Quality contour on this tree. 2.0.5 remains the previous published GitHub Latest until a human last mile.
```

HEAD `CHANGELOG.md:5`:

```
Quality contour: Ruff, Bandit, coverage ratchet, no GitHub Actions.
```

Section `## 2.0.6` has neither `until a human last mile` nor `2.0.5 remains`. Historical `## 2.0.4` “This-repo GitHub Actions…” bullet is left as history. Locked by `tests/test_structure.py::test_changelog_2_0_6_does_not_claim_stale_latest` (slices only the 2.0.6 section).

`dist/RELEASE-NOTES.md` (gitignored scratch; not in the commit) is a byte-for-byte copy of the cleaned §2.0.6. That stops the printer from restoring the stale sentence if a human re-runs `grok_deploy` on this working tree. A fresh clone still has the pre-existing “notes file is generated scratch” gap.

---

## 2. Installer quality configs — PASS

Parent `MANAGED_FILES` ended at the nine cwd shims. HEAD appends:

```34:36:scripts/install_into.py
    'ruff.toml',
    'bandit.yaml',
    '.coveragerc',
```

Those three files exist at repo root. `iter_source_files` now lists them; default install copies them via the existing `shutil.copy2` path. `--with-ci` still `SystemExit`s `forbidden` before any copy. `detect_repo` still only treats `pyproject.toml` / `requirements.txt` as `python:project`; copying `ruff.toml` does not flip kind.

Locked by `tests/test_installer.py::test_default_install_copies_quality_configs` (byte-identical copy of all three + no `.github/workflows`). Existing `test_default_install_does_not_copy_workflow_from_grok_stack` still holds.

Consumer with a *different* `ruff.toml` now hits the existing conflict/`--force` gate. That is the managed-file contract, not a new service.

---

## 3. Deploy `--title` — PASS

Parent `_human_commands` printed:

```
gh release create v{version} packages/{zip_name} packages/{zip_name}.sha256 --notes-file dist/RELEASE-NOTES.md
```

HEAD `deploy.py:33` inserts `--title "Adaptive Grok Build Pro v{version}"` before `--notes-file`. `scripts/grok_deploy.py` is still a thin printer: no `subprocess`, no `os.system`. Runbook `publish-v2.0.6.md:27` matches the same argv for `v2.0.6`.

Locked by `tests/test_deploy.py::test_dry_run_ready_is_ok_without_receipt` asserting `--title "Adaptive Grok Build Pro v{version}"`. Source still has no publish-exec imports (`test_prepare_sources_do_not_execute_publish_commands`).

Residual (documented, not a fail): `VERSION` is still `2.0.6`, so the printer still emits `gh release create v2.0.6`. Humans must not re-create that tag.

---

## 4. `__version__` — PASS

Parent `.grok-stack/adaptive_grok/__init__.py:3` was `__version__ = "2.0.0"`.  
HEAD is `__version__ = "2.0.6"`.  
`VERSION` is still `2.0.6`.

Hardcoded rather than read-from-`VERSION` (analysis allowed either). Drift is locked by `tests/test_structure.py::test_package_version_matches_version_file`. Packager and deploy still read `VERSION`, not this symbol.

---

## 5. MANIFEST unlink — PASS

Parent `write_archive` generated root `MANIFEST.sha256`, zipped `included_files` + that file, and returned. No unlink. `.gitignore` did not mention it. That leftover later failed `test_project_doctor_has_no_failures` (doctor verifies-if-present).

HEAD `scripts/package_stack.py:32-33`:

```python
leftover = root / 'MANIFEST.sha256'
leftover.unlink(missing_ok=True)
```

Order is generate → zip (`writestr` copies bytes) → sibling `.sha256` → unlink. Zip still embeds `adaptive-grok-build-pro/MANIFEST.sha256` because the member is added *before* unlink. `included_files` still excludes the root leftover (`EXCLUDED_FILES` contains `MANIFEST.sha256`); the explicit append is unchanged.

`.gitignore` now has `MANIFEST.sha256` with a one-line reason. Doctor still verifies-if-present (`doctor.py:86-94`); missing file is `info`, not fail.

Locked by `tests/test_manifest_package.py::test_write_archive_unlinks_root_manifest_but_embeds_it`. Existing `test_archive_is_deterministic_and_self_verifying` still requires the zip member.

`missing_ok=True` is fine on the product’s Python 3.12 floor. A failed zip before unlink can still leave a leftover; gitignore + doctor-if-present keep that from becoming a commit or a hard doctor fail on a clean tree.

---

## 6. AGENTS.md warn-only — PASS

Parent `AGENTS.md:99`:

```
The Stop hook blocks completion while required evidence is missing or stale.
```

HEAD:

```
The Stop hook warns when required evidence is missing or stale.
```

Matches the live hook: `.grok/hooks/stop_gate.py` is “soft (warn only, never block stop)” and emits a `systemMessage` without `decision=block`. Root `stop_gate.py` is still the fail-open shim. README:131 already said “Missing evidence is a Stop warning, not a hard block.” CHANGELOG 2.0.4 already said warn-only. `install_into.merge_agents` ships the corrected `AGENTS.md` into consumers.

No new Stop-hook test. Requirements only demanded installer + deploy title + changelog regressions; hook *behavior* was already warn-only.

---

## Scope and contracts — PASS

| Guard | Observed |
| --- | --- |
| Identity stays 2.0.6 | `VERSION` = `2.0.6`; README H1 untouched; no tag rewrite |
| No GHA / Dependabot | `.github/` absent; `--with-ci` still forbidden; template `github-actions.yml` absent |
| No packaging markers | `pyproject.toml` / `requirements.txt` / `setup.py` absent |
| No zip rebuild | `packages/…-v2.0.6.zip.sha256` still `55406ff22f81ae05fc70eb9a5710b5c055c76a18f2ddbe60687c03b3e0b95c4d` (published identity) |
| No push | `origin/main` still `e75f3a1` |
| No new service / SaaS | installer/deploy/packager only; no toolchain pin added for ruff/bandit/coverage |
| Tests-first regressions | five new assertions named in `test-plan.md`; parent `test_structure.py` lacked the two new methods |
| Smallest vertical | product + tests + runbook + gitignore; no verification.py rewrite |

The optional “gate coverage wrap on `.coveragerc` exists” item from analysis was not taken. Default install now copies `.coveragerc`, so the high-severity consumer fail-close is fixed on the intended path. Leaving the wrap unconditional is acceptable.

---

## Findings

No functional, security, or scope-break findings that fail the six-fix contract.

### Nits (do not fail)

1. **`__version__` is hardcoded.** A later `VERSION` bump will fail `test_package_version_matches_version_file` until someone edits `__init__.py`. Intended lock, not a live bug.
2. **`dist/RELEASE-NOTES.md` is not in commit `11da31a`.** Gitignored. Working tree is cleaned. A clone without `dist/` still has the pre-existing notes-file scratch gap.
3. **No AGENTS.md wording test.** Docs-only; hook behavior was already covered elsewhere.
4. **`generate_manifest()` alone still writes a root leftover.** Only `write_archive` unlinks. That is the packager entry humans run. gitignore covers accidental add.

---

## Residual risk

- Printer still emits `gh release create v2.0.6` because identity is 2.0.6. Do not re-create the published tag from this leftover commit.
- Tracked `packages/v2.0.6.zip` does **not** contain these leftover fixes. Shipping them to GitHub Latest would need a later, separately approved 2.0.7 (or an explicit rebuild+retag, which this route forbids).
- Consumers who copy CLIs by hand and skip `install_into` still miss `ruff.toml` / `bandit.yaml` / `.coveragerc`. The installer path is fixed.
- Could not independently run `python3 -m unittest` or `git show 11da31a`. File-level parent-vs-HEAD comparison was done via GitHub raw `e75f3a1` + local `HEAD`.

Rollback: revert `11da31a`. Do not restore GHA, `pyproject.toml`, or a VERSION bump. Do not retarget `v2.0.6`.

---

## Recommendation

**PASS.** All six required fixes are present on `11da31a`, locked by the named tests, and stay inside the 2.0.6 leftover-bug contract. Do not tag, push, or `gh release` from review.
