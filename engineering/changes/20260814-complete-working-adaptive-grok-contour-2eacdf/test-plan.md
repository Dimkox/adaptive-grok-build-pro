# Test plan — Complete working Adaptive Grok contour

## Characterization / failing first

Land these against the current tree before `_python` edits.

### A1 — passing unittest without a Python-project marker (`tests/test_verification_doctor.py`)

`project_copy(git=True)`, no `pyproject.toml` / `requirements.txt` / `setup.py`, write a passing `tests/test_ok.py`, `set_active_route`, `verify(record=True)`.

Assert: a check named `python-unittest` exists and `status == 'pass'`.

Fails today: `_python` returns `[]`.

### A2 — failing unittest fails verify

Same fixture with `tests/test_fail.py` that `self.fail(...)`.

Assert: `report['status'] == 'fail'` and `python-unittest` is `fail`.

### B5 — contour (`tests/test_change_receipts.py`)

`project_copy(git=True)`: `build_route` + required evidence `verification`, `code_review`, `test_review` → `start_change` → write passing `tests/test_ok.py` and dummy review report files → `verify(record=True)` → `write_receipt` for `code_review` and `test_review` with `pass` → `validate_evidence == []`.

Assert `python-unittest` passed. Never `verify(ROOT)`.

### A3 / A4 — skip when there is no unittest suite (green now)

A3: no `tests/` and no marker → `_python` returns `[]`.
A4: `tests/` contains only PHP (or other non-`test*.py`) → `_python` returns `[]`.

### Keep green

`test_verify_records_receipt_for_active_route` (no `tests/`, so no `python-unittest` check).

## Verification

```bash
python3 -m unittest discover -s tests
python3 scripts/grok_doctor.py
python3 scripts/grok_verify.py --mode pr --no-record
```

After implementation, `grok_verify --mode pr` (with record) must include `python-unittest` on this repo. Record the completion receipt only after the last change-package write.

## Residual

If pytest is on PATH and a consumer adds `pyproject.toml`, unittest is skipped by design. Wrapped-shell production commands stay unmatched.
