# Requirements — Complete working Adaptive Grok contour

## Acceptance criteria

- [x] Given a repo with `tests/test_ok.py` and no `pyproject.toml` / `requirements.txt` / `setup.py`, when `verify(..., record=True)` runs, then a `python-unittest` check exists and its status is `pass`
- [x] Given a repo with a failing `tests/test_fail.py` and no Python-project marker, when `verify` runs, then overall status is `fail` and `python-unittest` is `fail`
- [x] Given `project_copy(git=True)` with an active route, when the contour walks `start_change` → passing `tests/test_ok.py` → `verify(record=True)` → `write_receipt` for `code_review` and `test_review`, then `validate_evidence` is empty and `python-unittest` passed
- [x] Given a `project_copy` with no `tests/test*.py`, when `verify` runs, then there is no `python-unittest` check (existing receipt test still passes)
- [x] Given a Python-project marker and pytest available, when pytest is run, then `python-unittest` is not also run
- [x] README H1 is `Adaptive Grok Build Pro v2.0.4`
- [x] QUICKSTART verify fence closes before the `/hooks-trust` step
- [x] CHANGELOG 2.0.4 mentions that `grok_verify` runs `python-unittest` when a unittest suite exists

## Failure and edge cases

- `verify(ROOT)` from inside the suite would recurse; contour tests must use `project_copy` only
- Wrapped-shell production commands stay unmatched (accepted residual from 757a43)
- Follow-up tokens still reuse a leftover route (intended)

## Non-functional requirements

- Security: fail-closed gates unchanged
- Reliability: hooks stay fail-open on exception
- Performance: unittest timeout stays in the existing 900s command-check budget
- Observability: check name is `python-unittest`
