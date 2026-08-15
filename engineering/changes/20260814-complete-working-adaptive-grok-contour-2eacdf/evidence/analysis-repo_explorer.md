# Analysis — repo_explorer

Change: `20260814-complete-working-adaptive-grok-contour-2eacdf`
Route: `2eacdf08f448`

## Already fixed (uncommitted 757a43 baseline)

- `policy.py` matches production as argv prefixes, not path/arg words
- `router.py` `repair` keyword + `should_reuse_active_route`
- `user_prompt_submit.py` follow-up-only reuse; `_lib.is_child_payload` keeps parent route
- `.grok/hooks/adaptive.json` path-qualified; no stray root hook copies
- Stop is warn-only (2.0.4)

## Remaining breaks (ranked)

1. **Hollow verify (product).** `.grok-stack/adaptive_grok/verification.py` `_python` returns `[]` unless `pyproject.toml` / `requirements.txt` / `setup.py` exist. This repo has `tests/` and none of those markers. `make verify` / `grok_verify --mode pr` run only `git-diff-check`, `secret-scan`, `contract-structure`, `sql-safety`. Advertised contour can pass without executing ~95 unit tests.
2. **No contour characterization.** `tests/test_change_receipts.py` covers start/transition/stale receipts, not route → change → verify → review → `validate_evidence == []` with a real `python-unittest` check.
3. **Doc drift.** README H1 still `v2.0.3`; VERSION is `2.0.4`. `QUICKSTART.md` never closes the verify fence; step 7 `/hooks-trust` is inside the bash block.
4. **Not contour breaks.** `grok_change` has `show`, not `status` — `grok_status.py` is the status tool. packages/ stop at 2.0.3 (release, out of scope). HIGH_RISK substring scoring (separate). Wrapped-shell production misses (accepted 757a43 residual).

## Tests that exist vs missing

Covered: policy invocation, rematch, child skip, Stop warn-only, receipts stale/fail, doctor, installer, structure.
Missing: unittest-without-marker; failing unittest fails verify; full contour walk.
