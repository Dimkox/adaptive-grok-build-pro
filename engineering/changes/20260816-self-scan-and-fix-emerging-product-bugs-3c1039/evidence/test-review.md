# Test review — `3c10395cf76e`

Change: `engineering/changes/20260816-self-scan-and-fix-emerging-product-bugs-3c1039`  
Reviewer: `test_reviewer` (read-only). Write owner: `general_implementer`.  
Reviewed tree: product + tests from `11da31a` (installer configs, deploy title, CHANGELOG, `__version__`, manifest unlink).  
Suite was **not** re-run here (would dirty receipts / coverage artifacts). Independent file review of the four test files plus the product sites they lock, plus the official verification receipt.

**PASS.**

Required characterization for the five `11da31a` regressions is present, isolated, and would fail if the pre-fix tree came back. Official `python3 scripts/grok_verify.py --mode pr` on this fingerprint is **181 tests, OK**. Do not return this to `general_implementer` for test gaps.

| ID | Required case | Test | Result |
| --- | --- | --- | --- |
| P0 | Default install copies `ruff.toml`, `bandit.yaml`, `.coveragerc` | `tests/test_installer.py::test_default_install_copies_quality_configs` | Covered |
| P0 | Deploy printer includes `--title "Adaptive Grok Build Pro v{version}"` | `tests/test_deploy.py::test_dry_run_ready_is_ok_without_receipt` | Covered |
| P0 | CHANGELOG §2.0.6 does not contain last-mile / `2.0.5 remains` | `tests/test_structure.py::test_changelog_2_0_6_does_not_claim_stale_latest` | Covered |
| P0 | `write_archive` unlinks root `MANIFEST.sha256` but zip still embeds it | `tests/test_manifest_package.py::test_write_archive_unlinks_root_manifest_but_embeds_it` | Covered |
| P1 | `__version__` equals `VERSION` | `tests/test_structure.py::test_package_version_matches_version_file` | Covered |

---

## Verdict

| Gate | Result |
| --- | --- |
| Product-test adequacy for this delta | **PASS.** Four new methods plus one assertion in an existing deploy test lock every test-plan row. |
| Characterization coverage | **PASS.** Each new assertion matches the pre-fix failure mode recorded in `evidence/implementation.md`. Nearby keep-GHA / VERSION / zip-exclude tests were not weakened. |
| Verification evidence | **PASS.** Receipt exists, status `pass`, `python-unittest` `Ran 181 tests in 39.483s` / `OK`, fingerprint matches `last-fingerprint.json`. |

---

## 1. Tests added in `11da31a`

### 1.1 Installer quality configs — `test_default_install_copies_quality_configs`

Calls real `install_into.install(ROOT, target)` (stdout + toolchain runner silenced). Asserts each of `ruff.toml`, `bandit.yaml`, `.coveragerc` is a file on the target and **byte-equal** to the product source. Re-asserts default install still creates no `.github/workflows`.

This is the load-bearing consumer regression: `MANAGED_FILES` previously omitted those three names, so a default install left `grok_verify` fail-closed on copied `scripts/grok_*.py` (ruff E402, bandit B404/B603/B607, missing `.coveragerc`). Dropping any name from `MANAGED_FILES` now fails this test. `iter_source_files` only copies `MANAGED_FILES` + managed dirs; root configs are not under `.grok` / `.agents` / `.grok-stack`, so the test cannot pass via an accidental directory walk.

Keeps the adjacent lock `test_default_install_does_not_copy_workflow_from_grok_stack`. `--with-ci` remains `forbidden`.

### 1.2 Deploy title — `test_dry_run_ready_is_ok_without_receipt`

Existing dry-run case now also asserts

`--title "Adaptive Grok Build Pro v{version}"`

with `version` read from the fixture `VERSION` (copied by `project_copy`). That is version-dynamic: it will not rot when `VERSION` moves, and it still fails if the printer drops `--title` or hardcodes a stale product name. `_human_commands` in `deploy.py` is the only source of `gh release create` argv; the CLI is a thin print of that list.

Same test still locks `gh release create v{version}`, `--notes-file dist/RELEASE-NOTES.md`, package/copy/tag/push, and no deploy receipt on dry-run.

### 1.3 CHANGELOG §2.0.6 — `test_changelog_2_0_6_does_not_claim_stale_latest`

Reads `CHANGELOG.md`, slices from `## 2.0.6` to the next `## ` heading, and forbids the two fragments of the leftover sentence (`until a human last mile`, `2.0.5 remains`). Reverting line 5 to the pre-fix lead fails both assertions. Historical §2.0.4 “This-repo GitHub Actions…” is outside the slice, which is correct.

### 1.4 `__version__` — `test_package_version_matches_version_file`

`from adaptive_grok import __version__` must equal `VERSION` strip. Combined with existing `test_version_is_2_0_6_and_github_actions_are_absent` (`VERSION == 2.0.6`), both-wrong-but-equal (`2.0.0`/`2.0.0`) cannot sneak through. The new test is not hardcoded, so a later honest bump stays green if both files move together.

### 1.5 Manifest unlink — `test_write_archive_unlinks_root_manifest_but_embeds_it`

Temp tree → `PACKAGE.write_archive` → root `MANIFEST.sha256` must be gone; zip member `adaptive-grok-build-pro/MANIFEST.sha256` must exist and be non-empty. That is exactly the doctor landmine: `generate_manifest` still writes the root file for the zip copy; `unlink(missing_ok=True)` must run after `writestr`. Removing the unlink leaves the leftover and fails. Unlinking before the zip read raises `FileNotFoundError`. Never generating a manifest fails the member assertion.

Existing `test_archive_is_deterministic_and_self_verifying` still requires the in-zip member, so embed is double-locked.

---

## 2. Product sites the tests actually hit

| Product | What tests lock | Independent read |
| --- | --- | --- |
| `scripts/install_into.py` `MANAGED_FILES` | last three names `ruff.toml`, `bandit.yaml`, `.coveragerc` | Present at lines 34–36; copied via `iter_source_files` + `shutil.copy2` |
| `.grok-stack/adaptive_grok/deploy.py` `_human_commands` | `--title "Adaptive Grok Build Pro v{version}"` on the `gh release create` line | Present at line 33 |
| `CHANGELOG.md` §2.0.6 lead | no stale fragments | Line 5 is `Quality contour: Ruff, Bandit, coverage ratchet, no GitHub Actions.` |
| `.grok-stack/adaptive_grok/__init__.py` | `__version__ == VERSION` | `__version__ = "2.0.6"`; `VERSION` is `2.0.6` |
| `scripts/package_stack.py` `write_archive` | leftover unlink after zip | `leftover.unlink(missing_ok=True)` after digest write |

`engineering/runbooks/publish-v2.0.6.md:27` matches the printer title. Docs-only; not required as a unit test.

---

## 3. Verification evidence (did not re-run)

Did **not** re-run `python3 scripts/grok_verify.py --mode pr`. Re-running writes `.grok-stack/runtime/receipts/` and would mutate the tree. Re-read the official receipt instead.

Path: `.grok-stack/runtime/receipts/3c10395cf76e/verification.json`

| Field | Value |
| --- | --- |
| `created_at` | `2026-08-16T19:20:59+00:00` |
| `kind` / `mode` | `verification` / `pr` |
| `status` | `pass` |
| `profiles` | `base` |
| `route_id` | `3c10395cf76e` |
| `tree_fingerprint` | `0aef5401505de7624fd81de30d7a5606e2fe30830551c1d6c8ed9e162825dfec` |
| `last-fingerprint.json` | same digest — receipt is current as of this review |
| `python-unittest` | `status=pass`, `summary=exit=0`, stderr `Ran 181 tests in 39.483s` / `OK` |
| `ruff` / `bandit` / `coverage` | pass; coverage TOTAL **76%** (fail-under 74) |
| `git-diff-check` / `secret-scan` / contracts / sql | pass |

`changed_files` in that receipt include the four test files and the product files this review inspected: `tests/test_installer.py`, `tests/test_deploy.py`, `tests/test_structure.py`, `tests/test_manifest_package.py`, `scripts/install_into.py`, `scripts/package_stack.py`, `.grok-stack/adaptive_grok/deploy.py`, `.grok-stack/adaptive_grok/__init__.py`, `CHANGELOG.md`, `AGENTS.md`, `.gitignore`.

Writing this report will stale the receipt. Controller rebinds after reviews.

Implementer also recorded a focused `unittest` of the four modules plus discover **181 OK** in `evidence/implementation.md`. That matches the official receipt count. Pre-fix failures listed there are the same five assertions reviewed above.

---

## 4. Surrounding suite (not weakened)

| File | Still adequate? |
| --- | --- |
| `test_installer.py` `--with-ci` forbidden; no workflow copy | Yes. New test repeats the no-workflow half. |
| `test_deploy.py` print-only sources; no GHA/Dependabot | Yes. Title was added to the existing ready dry-run, not a parallel weaker case. |
| `test_structure.py` `VERSION==2.0.6`; no packaging markers; no workflows | Yes. New tests sit next to those pins. |
| `test_manifest_package.py` zip follows VERSION; no GHA in include set; excludes `.env` / `err.log` | Yes. Unlink test is additive. |
| `test_hooks.py` `test_stop_warns_without_evidence` | Yes. Hook remains warn-only (`decision != block`). AGENTS.md wording change is docs of that already-tested behavior. |
| `test_verification_doctor.py` doctor green; contour; ruff/bandit/coverage | Yes. Unlink removes the leftover that previously failed `test_project_doctor_has_no_failures`. |

Identity stays 2.0.6. No test reintroduces GHA, Dependabot, `pyproject.toml`, or a live `gh release` / tag assertion.

---

## 5. Gaps (not fail)

- Title is asserted in the joined command string, not as a same-line fragment of `gh release create`. A dummy extra command containing the title string would still pass. Residual only: `_human_commands` is a six-line list and the real create line is the only place that string lives.
- `test_cli_prints_commands_on_success` still only checks `package_stack.py` in CLI stdout. The CLI prints `prepare_deploy` commands; the library test is the contract.
- CHANGELOG test is a negative phrase lock, not a positive lead-text lock. A rewritten §2.0.6 that avoided those two fragments but still implied 2.0.5 is Latest would pass. Adequate for the leftover sentence that actually shipped.
- `dist/RELEASE-NOTES.md` is gitignored scratch and has no test. On-disk copy is already the cleaned lead. `grok_deploy` still points at it; regenerating notes from CHANGELOG after this lock stays honest.
- `.gitignore` `MANIFEST.sha256` is not unit-tested. Behavior under test is `write_archive` unlink; doctor still verifies-if-present. Calling `generate_manifest` alone still plants a leftover — that is not the packager path.
- AGENTS.md “warns” vs “blocks” has no string test. Runtime is already covered by `test_stop_warns_without_evidence`.
- Optional analysis item (gate coverage wrap on `.coveragerc` presence) was not implemented and is not in the test plan. After default install the rcfile is now copied, which is the chosen fix.

None of these would let the five `11da31a` regressions return unnoticed.

---

## Verdict (repeat)

**PASS.** Tests added in `11da31a` are adequate for installer quality configs, deploy `--title`, CHANGELOG §2.0.6 honesty, `__version__`/`VERSION`, and packager leftover unlink. Official verify is 181 OK on fingerprint `0aef5401…`. Do not return this to `general_implementer` for test gaps.
