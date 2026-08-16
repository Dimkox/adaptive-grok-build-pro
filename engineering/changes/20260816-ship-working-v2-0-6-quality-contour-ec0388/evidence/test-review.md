# Test review — `ec0388060302`

Change: `engineering/changes/20260816-ship-working-v2-0-6-quality-contour-ec0388`  
Reviewer: `test_reviewer` (read-only). Write owner: `general_implementer`.  
Reviewed tree: local `549f29d` quality contour. Suite was **not** re-run (would dirty receipts / coverage artifacts). Independent file review of `tests/test_verification_doctor.py` plus supporting tests and the measured `.coveragerc`.

**PASS.**

Required characterization and fail cases for the 2.0.6 contour are present, isolated, and would fail if `_python` went back to marker-gated ruff or dropped `python-unittest` on an unmarked tree. Existing contract / sql / secret-scan / doctor / contour / CI-identity tests remain. File inventory of `^\s+def test_` across `tests/` is **173** methods, matching the claimed 173 OK.

| ID | Required case | Test | Result |
| --- | --- | --- | --- |
| 1 | Marker-less tree still emits `python-unittest` (including with ruff on PATH) | `test_python_runs_unittest_without_project_marker`; `test_unmarked_tree_with_ruff_still_runs_unittest` | Covered |
| 2 | pytest-wins still characterized; ruff/bandit run first | `test_python_pytest_wins_when_project_marker_present`; `test_pytest_wins_but_ruff_and_bandit_run_first` | Covered |
| 3a | Unused import in a QUALITY path → `ruff` fail | `test_unused_import_in_quality_path_fails_ruff` | Covered |
| 3b | `eval` under `.grok-stack/adaptive_grok/` → `bandit` fail; same in `tests/` does not | `test_eval_in_product_path_fails_bandit`; `test_eval_only_in_tests_does_not_fail_bandit` | Covered |
| 4 | `secret-scan` still tested (complement, not replaced) | `test_secret_scan_detects_key`; `test_secret_scan_still_fails_when_bandit_present`; `test_missing_bandit_is_skip_and_secret_scan_remains` | Covered |
| 5 | Bucket B omit on this-shaped tree; signal + no binary → skip | `test_this_repo_shaped_tree_omits_bucket_b`; `test_semgrep_signal_without_binary_is_skip`; `test_trivy_signal_without_binary_is_skip` | Covered |
| 6 | `fail_under` is measured **74**, not invented 90; `fast` does not fail-under | `.coveragerc` + `evidence/coverage-baseline.md`; `test_fast_mode_does_not_fail_closed_on_coverage`; `test_coverage_fail_under_on_tiny_pr_fixture`; `test_coverage_skip_when_missing_in_pr_mode` | Covered |
| 7 | 173 tests reported OK | 173 `def test_` methods on disk; implementation note | Confirmed (not re-run) |
| Keep | Invalid contract / OpenAPI / SQL still fail | `test_invalid_json_contract_fails`; `test_invalid_openapi_structure_fails`; `test_unsafe_sql_fails` | Covered |
| Keep | Doctor green; contour evidence path | `test_project_doctor_has_no_failures`; `test_contour_route_change_verify_review_has_no_evidence_gaps` | Covered |
| Keep | CI template == root workflow; tools installed | `test_root_workflow_equals_template`; `test_workflow_installs_quality_tools` | Covered |
| Keep | No packaging markers on this product tree | `test_product_tree_has_no_packaging_markers` | Covered |
| — | Never `verify(ROOT)` | No matches in `tests/` | Honored |

---

## Independent review of `tests/test_verification_doctor.py`

The 2.0.6 work lives in `QualityContourTests` (16 cases) plus the older `VerificationTests` / `DoctorTests` that must stay green. Helpers are appropriate: `_PathTools` prepends fake CLIs; `_which_except` / `_which_only` pin presence; `_FAKE_RUFF` / `_FAKE_BANDIT` / `_FAKE_COVERAGE_FAIL_REPORT` isolate adapter wiring from host tool versions.

Control-flow characterizations match `_python` in `verification.py`:

- `results = [_ruff(root), _bandit(root)]` **before** the marker + pytest early return. `test_pytest_wins_but_ruff_and_bandit_run_first` asserts both result-list order and `_command_check` invocation order, and that `python-unittest` is absent.
- Marker-less + ruff present still takes the unittest branch (`test_unmarked_tree_with_ruff_still_runs_unittest`). That is the load-bearing 2.0.6 regression: ruff on PATH must not flip the tree into pytest-wins.
- Missing ruff / bandit / coverage are `skip`, not `fail`.
- Bandit path list drops `tests` (`verification.py` `_bandit`). The eval-in-tests case would fail the fake if `tests/` were passed through. Product `eval` is planted under `.grok-stack/adaptive_grok/_planted_eval.py`.
- Unused import is planted under `.grok-stack/adaptive_grok/_planted_unused.py`, which is in `QUALITY_PY_PATHS`. Fake ruff only fails when it sees that file among `ruff check` path arguments.
- `secret-scan` is still invoked from `verify()` on `changed_files`. The planted `config.php` is written after the fixture commit, so `git ls-files --others` includes it. Bandit on PATH does not swallow that fail.
- Coverage: `pr` wraps unittest with `coverage run` then `coverage report`; `fast` does not wrap and must not fail-closed. The fail-under fixture uses a stub that exits 1 on `report` — that tests the adapter, not coverage.py’s parser. Correct split: the number **74** is not hardcoded in Python (architect rule).
- Bucket B: no `package.json` / `Dockerfile` / `semgrep.yaml` on a `project_copy` → `semgrep`, `trivy-config`, and `npm-*` are absent. Signal without binary → `skip`. `npm-prettier` is emitted only when the script exists.
- No test calls `verify(ROOT)` (that would recurse until 900s). Doctor on `ROOT` is the intended exception.

`tests/_support.py` now copies `ruff.toml`, `bandit.yaml`, and `.coveragerc` into fixtures so real CLIs, when used, see the product config.

---

## Coverage number 74 (not 90)

Read from the tree, not from chat:

- `evidence/coverage-baseline.md`: coverage 7.15.4, suite 173 OK, TOTAL line **76%**, chosen `fail_under = floor(76) - 2` = **74**. Explicitly “a ratchet, not a handbook 90”.
- `.coveragerc` `[report] fail_under = 74`.
- Tests never assert 90. The pr fail fixture plants `fail_under = 100` only to force a report-nonzero through the fake.

`fast` skip is locked: `test_fast_mode_does_not_fail_closed_on_coverage` (fake report-fail on PATH, mode `fast`, unittest still pass, coverage absent or non-fail). Missing tool in `pr` is `skip` with unittest still pass.

---

## Surrounding suite

| File | Role for 2.0.6 |
| --- | --- |
| `tests/test_deploy.py` | Workflow installs ruff/bandit/coverage; still `unittest discover` + `grok_verify --mode pr`; template == root; no publish |
| `tests/test_structure.py` | No `pyproject.toml` / `requirements.txt` / `setup.py` (pytest-wins must not light on this tree) |
| `tests/test_change_receipts.py` | Contour still expects `python-unittest` pass on an unmarked `project_copy` |
| `tests/test_manifest_package.py` | Zip still follows `VERSION`; secrets / runtime still excluded |
| Other `tests/test_*.py` | Policy, hooks, toolchain, installer, bitrix, router, runtime — still present; 173 total |

---

## Gaps (not fail)

- Fake ruff/bandit string-match (`import unused_module`, `eval(`) rather than invoking real F401/B307. Adequate for adapter wiring; real first-run is in `evidence/ruff-first-run.md` (8 F401 → 0) and implementation (bandit exit 0).
- No unit test reads `.coveragerc` and asserts `74`. Intentional: number lives in config + baseline note, not Python.
- `test_unused_import_in_quality_path_fails_ruff` asserts the `ruff` check, not overall `verify()` status. `verify()` fails on any `fail` check; residual only.
- `npm-format`, empty `.semgrep/` dir, and `docker-compose*.yml` as a Trivy signal are untested. This tree has none of those files.
- No test pins Dependabot `github-actions` only, or that `htmlcov` / `.coverage.*` stay out of the zip.
- `test_this_repo_shaped_tree_omits_bucket_b` uses a `project_copy` (which never copies `package.json` / `Dockerfile`). Live root listing also has none of those signals.

None of these would let the contour regress on the seven must-confirm items.

---

## Verdict

**PASS.** Do not return this to `general_implementer` for test gaps. Official `python3 scripts/grok_verify.py --mode pr` and receipt binding remain the controller’s job after both reviews.
