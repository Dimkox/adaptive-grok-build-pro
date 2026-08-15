# Implementation — hollow-verify gap

Route: `2eacdf08f448` · write owner: `general_implementer`  
Change: `20260814-complete-working-adaptive-grok-contour-2eacdf`

Close the hollow-verify gap so `grok_verify` runs this product's unit tests when `tests/test*.py` exist, even without `pyproject.toml` / `requirements.txt` / `setup.py`. Not a release.

## Changed files

| File | Change |
| --- | --- |
| `.grok-stack/adaptive_grok/verification.py` | `_python` now runs `python-unittest` when `tests/test*.py` exist and no pytest-with-marker path ran; `import sys` |
| `tests/test_verification_doctor.py` | A1–A4 |
| `tests/test_change_receipts.py` | B5 `ContourTests` |
| `README.md` | H1 → `Adaptive Grok Build Pro v2.0.4` |
| `QUICKSTART.md` | Close the verify bash fence before step 7 `/hooks-trust` |
| `CHANGELOG.md` | 2.0.4 bullet: `grok_verify` runs `python-unittest` when `tests/test*.py` exist |

No `pyproject.toml` / `requirements.txt` / `setup.py`. No policy / router / hooks / stop_gate / `grok_change` / VERSION / package edits.

## Fail-first

Landed A1–A4 and B5 against the pre-`_python` tree.

```
python3 -m unittest \
  tests.test_verification_doctor.VerificationTests.test_python_runs_unittest_without_project_marker \
  tests.test_verification_doctor.VerificationTests.test_python_unittest_failure_is_a_failed_check \
  tests.test_verification_doctor.VerificationTests.test_python_skips_without_tests_or_project_marker \
  tests.test_verification_doctor.VerificationTests.test_python_ignores_non_python_tests_directory \
  tests.test_change_receipts.ContourTests.test_contour_route_change_verify_review_has_no_evidence_gaps \
  tests.test_verification_doctor.VerificationTests.test_verify_records_receipt_for_active_route
```

Result **before** `_python` edit: `FAILED (failures=3)`

- A1 `test_python_runs_unittest_without_project_marker` — FAIL: `python-unittest` check was `None`
- A2 `test_python_unittest_failure_is_a_failed_check` — FAIL: `report['status']` was `'pass'`
- B5 `test_contour_route_change_verify_review_has_no_evidence_gaps` — FAIL: `'python-unittest' not found`
- A3, A4, `test_verify_records_receipt_for_active_route` — PASS

## Commands + results (after `_python` and docs)

```
python3 -m unittest discover -s tests
```

`Ran 100 tests in 9.341s` — **OK** (exit 0)

```
python3 scripts/grok_doctor.py
```

All required checks **PASS**. `DOCTOR_EXIT=0`

```
python3 scripts/grok_verify.py --mode pr --no-record
```

```
PASS git-diff-check: exit=0
PASS secret-scan: 0 potential secrets
PASS contract-structure: 0 contracts checked
PASS sql-safety: 0 unsafe SQL findings
PASS python-unittest: exit=0
RESULT: PASS | profiles=base | changed=58
VERIFY_EXIT=0
```

Completion receipts were **not** recorded here. Parent binds `verification` / `code_review` / `test_review` after this last write.

## Residual risk

- If a consumer adds a Python-project marker and `pytest` is on PATH, `_python` runs pytest and skips unittest by design.
- Pytest-only files on an unmarked tree are collected by `unittest discover` and will fail that check.
- Wrapped-shell production command matching and HIGH_RISK substrings stay out of scope (accepted residual from 757a43).
- `grok_change status` is not a break; skills already use `scripts/grok_status.py`.

## Rollback

Revert:

- `.grok-stack/adaptive_grok/verification.py`
- `tests/test_verification_doctor.py`
- `tests/test_change_receipts.py`
- `README.md`, `QUICKSTART.md`, `CHANGELOG.md`

No data repair. Reverting `_python` restores hollow verify (unit tests not run by `grok_verify`). Prefer a forward-fix.

After rollback: `python3 -m unittest discover -s tests` and `python3 scripts/grok_doctor.py`.
