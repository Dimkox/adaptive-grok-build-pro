# Architecture — Complete working Adaptive Grok contour

## Decisions

1. **Unittest without a packaging marker.** If `tests/` contains `test*.py`, `verification._python` runs `[sys.executable, '-m', 'unittest', 'discover', '-s', 'tests']` as check `python-unittest`. Do not add `pyproject.toml` / `requirements.txt` / `setup.py` — those would flip `detect_repo` and currently *skip* this path.
2. **Pytest wins when it actually runs.** Keep ruff/pytest only when a Python-project marker exists. If pytest is invoked, skip unittest so the same suite is not run twice.
3. **Contour characterization, not live-tree verify.** Add `ContourTests` in `tests/test_change_receipts.py` on `project_copy(git=True)`. Never call `verify(ROOT)` from tests.
4. **Docs last, no release.** README H1 → v2.0.4; close the QUICKSTART fence; one 2.0.4 changelog bullet. No VERSION / package / tag / GitHub.
5. **`grok_change status` is not a break.** Skills already use `scripts/grok_status.py`; CLI `show` stays.

## Control flow (`_python`)

```
has_marker = pyproject.toml | requirements.txt | setup.py
if has_marker:
    ruff if present
    if pytest present and tests/ exists:
        run pytest
        return  # no unittest
if tests/ has test*.py:
    run python-unittest
```

## What does not change

`stop_gate.py`, production invocation matcher, rematch / child-skip, HIGH_RISK list, Bitrix/secret/destructive/MCP gates, installer, packaging, VERSION.
