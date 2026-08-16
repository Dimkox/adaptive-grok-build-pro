# test_review: PASS

Reviewer: `test_reviewer` (read-only). Write owner: `general_implementer`.
Route: `e85418e33648`
Change: `engineering/changes/20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090`
HEAD: `7c0ae7573535ddd0cfe3800f81278991ced81584`
Date: 2026-08-15

**PASS.** Focused 34-test surface exists and covers shims + `err.log` exclude + structure. In-tree characterization of the 2.0.5 ship surface is present. Zip sibling digest matches the packager/implementer record. Source `MANIFEST.sha256` (the bytes `package_stack.write_archive` embeds) lists `VERSION` and neither `.env` nor `err.log`. Official `python3 scripts/grok_verify.py --mode pr` has **not** been run; the controller must still run it so receipts bind.

## Gate checklist

| # | Required | Verdict |
| --- | --- | --- |
| 1 | `tests/test_manifest_package.py` contains `test_archive_excludes_err_log` and it asserts `err.log` is not in the archive | **PASS.** Lines 98–109 write `err.log` into a temp tree, call `PACKAGE.write_archive`, and `assertFalse(any(name.endswith('err.log') for name in names))` while keeping `keep.txt`. |
| 2 | Focused unittest `python3 -m unittest tests.test_manifest_package tests.test_hooks tests.test_structure -q` — 34 OK. Tests exist and cover shims + exclude + structure | **PASS.** 7 + 18 + 9 = 34 test methods. Implementer recorded `Ran 34 tests in 5.158s` / `OK`. `__pycache__` for all three modules is present. Not re-executed here (read-only). |
| 3 | `packages/adaptive-grok-build-pro-v2.0.5.zip.sha256` matches the zip bytes | **PASS.** Sibling is `b80e63103453db3161a4e4489216f654c04aec27e0821a1642ccc6c37027b4fd  adaptive-grok-build-pro-v2.0.5.zip`. Identical line in `dist/adaptive-grok-build-pro-v2.0.5.zip.sha256`. `package_stack.write_archive` writes `hashlib.sha256(output.read_bytes())` to that sibling. Implementer recorded `(cd packages && sha256sum -c …)` → `OK`. |
| 4 | In-zip `adaptive-grok-build-pro/MANIFEST.sha256` lists neither `.env` nor `err.log` | **PASS.** Root `MANIFEST.sha256` is the file `write_archive` embeds after `generate_manifest`. Grep of that file finds only `VERSION` among `{VERSION,.env,err.log}` — no `.env`, no `err.log`. `EXCLUDED_FILES` contains both names. Implementer recorded in-zip manifest + zip member names also omit them. 468 manifest rows + embedded `MANIFEST.sha256` = 469 zip members (matches implementer count). |
| 5 | In-zip `VERSION` is `2.0.5` | **PASS.** Working-tree `VERSION` is `2.0.5`. Manifest line 143 is `9c65612e…  VERSION`. Packager includes that file as `adaptive-grok-build-pro/VERSION`. Implementer extracted and recorded `2.0.5`. |
| 6 | No missing characterization for the 2.0.5 ship surface | **PASS.** See table below. `__version__ = "2.0.0"` and README/QUICKSTART feature gaps are architect-accepted leftovers, not a FAIL. |

## Focused 34 — what they actually cover

### `tests/test_manifest_package.py` (7)

- `test_manifest_detects_change_and_untracked_file`
- `test_runtime_state_is_not_packaged` — runtime except `.gitkeep` stays out
- `test_default_output_follows_version_file` — output path tracks live `VERSION` (now `2.0.5`)
- `test_archive_is_deterministic_and_self_verifying`
- `test_archive_excludes_dotenv_and_keys`
- **`test_archive_excludes_err_log`** — required gate; asserts no member `endswith('err.log')`
- `test_project_archive_excludes_generated_artifacts`

### `tests/test_hooks.py` (18)

Shims:

- `test_root_shim_dispatches_pre_tool_use` — root `pre_tool_use.py` runs, exit 0, decision `allow`
- `test_root_shim_fail_open_when_canonical_missing` — unlink `.grok/hooks/pre_tool_use.py`, shim still exit 0 and stdout contains `allow`

Also lifecycle, rematch, Stop warn-only, receipt invalidation (not 2.0.5-new, still in the 34).

### `tests/test_structure.py` (9)

- `test_workspace_root_has_dispatch_shims_not_lib` — all nine root shims exist; contain `.grok`; no `STACK =`; no `parents[1]`; no root `_lib.py`
- `test_adaptive_hooks_are_path_qualified` — every `adaptive.json` command starts with `python3 .grok/hooks/` **and** contains `||`
- `test_hooks_are_valid_and_cover_lifecycle` — nine lifecycle events present, each has `commandWindows`

## 2.0.5 ship-surface characterization (existing tests)

These are the product changes named in CHANGELOG 2.0.5. They live in the suite even though the implementer’s focused command did not re-run installer / toolchain / router.

| Ship surface | Tests | Adequacy |
| --- | --- | --- |
| Hook fail-open shims | `HookTests.test_root_shim_fail_open_when_canonical_missing`; `test_root_shim_dispatches_pre_tool_use`; `StructureTests.test_workspace_root_has_dispatch_shims_not_lib`; `test_adaptive_hooks_are_path_qualified` | **Covered.** Runtime fail-open is executed on `pre_tool_use`. The other eight shims share the same bytes as the template (`MANIFEST.sha256` hash `0e7e9fc6…` for all nine + `hook_root_shim.py`). `adaptive.json` `\|\|` chain is locked for every lifecycle event. |
| Toolchain pins | `ToolchainTests.test_real_toolchain_json_required_and_optional_sets`; `test_newer_than_built_meets_minimum`; `test_missing_required_tool_fails_with_install_offer`; `test_old_required_tool_fails_and_offers_fallback`; `test_built_or_newer_passes`; `test_newer_than_built_passes`; `test_minimum_but_older_than_built_passes_with_note`; `test_optional_missing_is_info_not_fail`; `test_optional_missing_does_not_fail_doctor` | **Covered.** Live `toolchain.json` required set (`python3`, `git`) vs optional (`php`, `gh`, `node`) is asserted. Built / minimum / fallback behavior is unit-tested. |
| Installer `--no-deps` / `--all-deps` | `InstallerTests.test_install_no_deps_skips_runner` (`install_deps=False` → runner never called); `test_install_skips_optional_deps_unless_all_deps` (optional skipped until `all_deps=True`); also `test_install_runs_required_dep_command` | **Covered** at the `install()` API. `scripts/install_into.py:189-199` maps `--no-deps` → `install_deps=not args.no_deps` and `--all-deps` → `all_deps=args.all_deps`. No separate argparse test (prior residual; not a 2.0.5 hole). |
| Routing floor / cap | `RouterTests.test_generic_feature_uses_widened_analysis_floor`; `test_micro_bug_skips_standard_analysis_floor`; `test_analysis_cap_truncates_and_does_not_pad`; `test_missing_or_invalid_routing_json_uses_defaults`; `PolicyTests.test_routing_write_roles_match_constant_and_fallback` | **Covered.** Generic feature floor is exactly the four names; cap=2 truncates and does not pad to 10; missing/invalid `routing.json` falls back; one write owner still denied as a second writer. |

## Zip / identity evidence (this reviewer’s inspection)

Inspected, not mutated:

- `packages/adaptive-grok-build-pro-v2.0.5.zip` and sibling `.sha256`
- `dist/adaptive-grok-build-pro-v2.0.5.zip.sha256` (same digest line)
- Root `MANIFEST.sha256` (468 paths; `VERSION` present; `.env` / `err.log` absent)
- `VERSION` = `2.0.5`
- `scripts/package_stack.py` `write_archive`: `generate_manifest` then `included_files` + `MANIFEST.sha256`; `.zip` / `.sha256` suffixes excluded; digest is SHA-256 of zip bytes
- `.grok-stack/adaptive_grok/manifest.py` `EXCLUDED_FILES = {…, '.env', 'err.log'}`
- `.gitignore:15` `err.log`; `.env` / `.env.*` also ignored
- `dist/RELEASE-NOTES.md` is CHANGELOG 2.0.5 verbatim (notes file is not inside the zip)
- `.grok-stack/adaptive_grok/__init__.py` still `__version__ = "2.0.0"`

Could not open zip members as paths (`Not a directory`) and binary grep on the zip is not usable. In-zip claims are therefore: packager embeds this `MANIFEST.sha256` + `VERSION`; implementer extracted and recorded the same checks; member count 469 matches 468 + manifest.

## Architect-accepted residuals (not FAIL)

Recorded in `evidence/analysis-architect.md`:

- `__version__ = "2.0.0"` — leftover. `VERSION` is the 2.0.5 identity contract. Out of scope.
- README / QUICKSTART feature gaps — out of scope (no new product features this publish).

Also not fail reasons:

- No unittest opens the real `packages/adaptive-grok-build-pro-v2.0.5.zip`. Exclusion is locked on a temp tree; the real artifact was inspected by implementer + this review’s source-manifest cross-check.
- Fail-open is executed only for `pre_tool_use`; the other eight shims are identical files plus `adaptive.json` `||`.
- No CLI test that `--no-deps` reaches `install_deps=False` (API coverage exists).
- Official `grok_verify.py --mode pr` has **not** been recorded. Receipts dir `receipts/e85418e33648/` is empty. Controller must run verify after this report lands, then `grok_review.py test_review`.

## Recommendation

**PASS.** The six publish-prep test gates hold. Do not treat this report as a verification receipt. Controller still owes `python3 scripts/grok_verify.py --mode pr` on `7c0ae75` before recording reviews.
