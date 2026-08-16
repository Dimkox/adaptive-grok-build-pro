# Test review — `5be23b16d59f` / `e75f3a1`

Change: `engineering/changes/20260816-finish-2-0-6-commit-ban-verify-github-release-5be23b`  
Reviewer: `test_reviewer` (read-only). Write owner: `general_implementer`.  
Reviewed tree: `refs/heads/main` = `e75f3a1b92e247279fbb6210d46715a90cf7895c` (`Release v2.0.6: ban GitHub Actions, rebuild zip`). Parent `549f29d`.  
Did **not** re-run the suite (would rewrite receipts / coverage artifacts). Inspected the committed tests, `install_into.py`, CI README, and the official `grok_verify --mode pr` receipt.

**PASS.**

The GHA-ban contract is inverted, isolated, and would go red if `--with-ci` started writing again, if a workflow / Dependabot / template YAML returned, or if the shipped 2.0.6 zip contained Actions. Official verify on this tree is green: ruff, bandit, 177 unittests, coverage.

| ID | Required case | Test | Result |
| --- | --- | --- | --- |
| 1 | `install(..., with_ci=True)` refuses; writes no workflow; leaves unrelated YAML | `test_with_ci_is_forbidden_and_preserves_unrelated_workflow` | Covered |
| 2 | Same refuse under `--force --dry-run`; no stack files written | `test_with_ci_dry_run_is_forbidden_and_writes_nothing` | Covered |
| 3 | Default install does not copy a workflow from `.grok-stack` | `test_default_install_does_not_copy_workflow_from_grok_stack` | Covered |
| 4 | Working tree has no `adaptive-grok.yml` and no `github-actions.yml` | `test_repo_has_no_github_actions_workflow_or_template` | Covered |
| 5 | No `.github/workflows/*.yml`; no Dependabot | `test_repo_has_no_workflow_yaml_or_dependabot`; `test_version_is_2_0_6_and_github_actions_are_absent` | Covered |
| 6 | CI README bans Actions and is not a publisher | `test_ci_readme_bans_github_actions_and_is_not_a_publisher` | Covered |
| 7 | `included_files()` + shipped zip: VERSION 2.0.6, no workflows / Dependabot / template | `test_included_files_and_shipped_zip_have_no_github_actions` | Covered |
| 8 | Old “workflow exists and equals template” contract is gone | no `test_root_workflow_equals_template` / `test_workflow_installs_quality_tools` / `test_with_ci_preserves_unrelated_workflow` | Inverted |
| 9 | `grok_verify --mode pr` PASS (ruff / bandit / unittest / coverage) | receipt `.grok-stack/runtime/receipts/5be23b16d59f/verification.json` | Confirmed (not re-run) |
| Keep | Existing installer / deploy / structure / package tests | `tests/test_installer.py`, `tests/test_deploy.py`, `tests/test_structure.py`, `tests/test_manifest_package.py` | Still present |
| Keep | Quality contour (unittest on unmarked tree; ruff/bandit first) | `tests/test_verification_doctor.py` | Untouched, still in suite |
| — | Last-mile Latest = v2.0.6 / v2.0.5 remains | observational; not a unit test | Out of product-test scope |

---

## Independent review of the ban tests

This route commits the already-implemented ban from `9fd274`. Product tests live in four files staged on `e75f3a1`. They replace the pre-ban contract (`549f29d` still shipped Actions).

### `tests/test_installer.py`

`install_silent` still calls `MODULE.install(...)` (not argparse). That matches the architect rule: reject must be inside `install()`, not an argparse-only dead flag.

- `test_with_ci_is_forbidden_and_preserves_unrelated_workflow` plants `existing.yml`, calls `with_ci=True` (`force=False`, `dry_run=False`), asserts `SystemExit` text contains `forbidden`, file bytes unchanged, no `adaptive-grok.yml`.
- `test_with_ci_dry_run_is_forbidden_and_writes_nothing` uses `force=True`, `dry_run=True`. Same refuse. Also asserts `scripts/grok_verify.py` was not copied — that is the load-bearing “raise before any copy” check. Matches `install()`:

```96:100:scripts/install_into.py
    if with_ci:
        raise SystemExit(
            'GitHub Actions is forbidden. Use local `make verify` / '
            '`python3 scripts/grok_verify.py --mode pr`.'
        )
```

No leftover copy block. The only `with_ci` branch is that raise. `--with-ci` remains on the parser so old callers fail loudly (`help` says forbidden; `main()` passes `args.with_ci` through).

- `test_default_install_does_not_copy_workflow_from_grok_stack` is the other ship path: `MANAGED_DIRS` includes `.grok-stack`, so deleting only the root workflow is not enough. It asserts no `.github/workflows`, no `github-actions.yml`, and no copied `*.yml` / `*.yaml` under those names. Pre-ban, every install would have shipped the template.

Existing installer cases (conflict/force, Bitrix `local/AGENTS.md`, deps runner, HTTP-manual, idempotent AGENTS block) remain.

### `tests/test_deploy.py`

`DeploySourceAndCiTests` no longer locks byte-identical workflow == template. Replacements:

- absence of `adaptive-grok.yml` and `templates/ci/github-actions.yml`
- empty `.github/workflows/*.yml` and no Dependabot
- `templates/ci/README.md` contains `never` + `github actions` and `grok_verify.py --mode pr` or `make verify`; must not contain `gh release` / `git push` / `docker push`

`test_prepare_sources_do_not_execute_publish_commands` still keeps `grok_deploy.py` print-only. Last mile stays GitHub CLI, not Actions.

### `tests/test_structure.py`

`test_version_is_2_0_6_and_github_actions_are_absent` pins `VERSION == 2.0.6` and the same three absences (workflows dir empty or missing, no Dependabot, no template YAML). `test_product_tree_has_no_packaging_markers` still forbids `pyproject.toml` / `requirements.txt` / `setup.py` so this tree cannot flip into pytest-wins.

### `tests/test_manifest_package.py`

`test_included_files_and_shipped_zip_have_no_github_actions` checks both the packager input list and the committed `packages/adaptive-grok-build-pro-v2.0.6.zip` namelist. In-zip `VERSION` is `2.0.6`. Zip half is gated on `zip_path.is_file()`; the file is present on `e75f3a1`, so the namelist assertions run.

On-disk confirmation from this review (not a command re-run): `.github/` does not exist; `.grok-stack/templates/ci/` is README only.

---

## Verification evidence

Did **not** re-run `python3 scripts/grok_verify.py --mode pr`. Re-read the route receipt.

Path: `.grok-stack/runtime/receipts/5be23b16d59f/verification.json`

| Field | Value |
| --- | --- |
| `created_at` | `2026-08-16T18:22:48+00:00` |
| `kind` / `mode` | `verification` / `pr` |
| `status` | `pass` |
| `profiles` | `base` |
| `route_id` | `5be23b16d59f` |
| `tree_fingerprint` | `22aa56aa559d8b287b4c4b45a443a62c56af3d4c4ebfadf0613ed2eb56f85213` |
| `git-diff-check` | pass |
| `secret-scan` | pass, `0 potential secrets` |
| `contract-structure` | pass |
| `sql-safety` | pass |
| `ruff` | pass, `All checks passed!` |
| `bandit` | pass, exit 0 |
| `python-unittest` | pass, `Ran 177 tests in 38.058s` / `OK` |
| `coverage` | pass, TOTAL **76%**, `fail_under = 74` in `.coveragerc` |

`last-fingerprint.json` matches that fingerprint at review start. Writing this report will stale it; that is paperwork, not a failed suite.

`changed_files` in the receipt include the ban surface (`scripts/install_into.py`, the four test files, CI README, deleted workflow/template paths, rebuilt zip) plus sibling change-package dirt. Unittest still collected 177 and passed; leftover `ad4090` / `864726` paperwork is not a test gap.

---

## Surrounding suite

| File | Role for this ban |
| --- | --- |
| `tests/test_installer.py` | Refuse `--with-ci`; default install does not ship YAML |
| `tests/test_deploy.py` | Repo + README lock; deploy remains print-only |
| `tests/test_structure.py` | VERSION 2.0.6; no GHA; no packaging markers |
| `tests/test_manifest_package.py` | Packager + shipped zip have no Actions |
| `tests/test_verification_doctor.py` | Local contour still unittest-first; ruff/bandit/coverage |
| Other `tests/test_*.py` | Policy, hooks, toolchain, router, receipts, Bitrix — still present; 177 OK |

Pre-ban `9fd274` recorded inverted tests going red on `549f29d` (7 fail + 1 error) before the product edit. That is the required failing/characterization step.

---

## Gaps (not fail)

- No subprocess test of `python3 scripts/install_into.py --with-ci`. By design: architect required `install(..., with_ci=True)`. `main()` (`install_into.py` 177–191) is uncovered; pass-through is one assignment. A later argparse-only reject would fail the existing `install()` tests.
- No dedicated `force=True, dry_run=False, with_ci=True` case. `force` is unused after the early raise. `force=True` is already on the dry-run case.
- `test_deploy` / `test_structure` glob `*.yml` only. A `.yaml` workflow would slip those two. Installer default-install rglob includes `.yaml`. Residual on this tree: `.github/` is absent.
- Zip namelist asserts only if the zip file exists. It exists on `e75f3a1`.
- Last-mile items in this package’s `test-plan.md` (GitHub Latest `v2.0.6`, `v2.0.5` still viewable) are publish observations, not product tests. Correctly untested here.

None of these would let `--with-ci` write a workflow or let Actions re-enter the tree / zip unnoticed.

---

## Verdict

**PASS.** Do not return this to `general_implementer` for test gaps. Last mile (tag / push / `gh release` on `e75f3a1`, not `549f29d`) remains the controller’s job after both reviews and a live production token.
