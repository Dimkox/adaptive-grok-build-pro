# Analysis — architect

Change: `20260814-complete-working-adaptive-grok-contour-2eacdf`
Route: `2eacdf08f448` · write owner: `general_implementer`

Close the hollow verify gap. Not a release. Do not reverse 757a43.

## Files

| File | Change |
| --- | --- |
| `.grok-stack/adaptive_grok/verification.py` | Rewrite `_python`; add `import sys` |
| `tests/test_verification_doctor.py` | A1–A4 |
| `tests/test_change_receipts.py` | B5 `ContourTests` |
| `README.md` | H1 → `v2.0.4` |
| `QUICKSTART.md` | Close verify fence before step 7 |
| `CHANGELOG.md` | One 2.0.4 bullet |

No `pyproject.toml`. No policy / rematch / Stop / `grok_change` / VERSION / package edits.

## `_python`

- `has_project` = `pyproject.toml` or `requirements.txt` or `setup.py`
- `has_unittest_files` = `tests/` has `rglob('test*.py')`
- If `has_project`: optional ruff; if pytest + `tests/` dir → `pytest -q` and **return**
- Elif `has_unittest_files`: `[sys.executable, '-m', 'unittest', 'discover', '-s', 'tests']` named `python-unittest`
- Else `[]`

Never `_python(ROOT)` / `verify(ROOT)` in tests.

## Fail-first

- **A1** `test_python_runs_unittest_without_project_marker` — passing `test_ok.py`, no marker → `python-unittest`/`pass`.
- **A2** `test_python_unittest_failure_is_a_failed_check` — failing case → `fail`.
- **A3** `test_python_skips_without_tests_or_project_marker` — `[]` (green now).
- **A4** `test_python_ignores_non_python_tests_directory` — PHP-only `tests/` → `[]` (green now).
- **B5** `test_contour_route_change_verify_review_has_no_evidence_gaps` — `project_copy(git=True)`: route + evidence `[verification, code_review, test_review]` → `start_change` → write test + review md **before** verify → `verify(fast, record=True)` asserts unittest pass → `write_receipt` both reviews → `validate_evidence == []`. No transition after receipts.

## Residual

`grok_verify` on this repo runs the full suite (so it must stay green). Pytest-only files on unmarked trees fail unittest discover. `grok_change status` is not a break. Wrapped-shell production misses and HIGH_RISK substrings stay out of scope.

## Order

1. Land A1–A4 + B5; confirm A1/A2/B5 fail.
2. Implement `_python` only.
3. `python3 -m unittest discover -s tests`
4. `python3 scripts/grok_verify.py --mode pr` shows `PASS python-unittest`
5. Docs last.
6. Bind receipts after the last tree write (parent orchestrator).
