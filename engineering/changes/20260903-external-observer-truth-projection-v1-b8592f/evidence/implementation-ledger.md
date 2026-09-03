# Implementation ledger

## 2026-09-03 — RED

- Command: `python3 -m unittest tests.test_external_observer -v`
- Result: exit 1, one import error: `adaptive_grok.external_observer` did not exist.
- Ruling: implement the frozen EO-001..EO-010 surface without real network calls in tests; preserve separate Observer authority and fail closed.

## 2026-09-03 — GREEN

- Focused behavior: `python3 -m unittest tests.test_external_observer -q` → 25 tests, PASS.
- Targeted integration: `python3 -m unittest tests.test_external_observer tests.test_structure tests.test_project_state tests.test_installer -q` → 60 tests, PASS.
- Contract proof: the happy projection validates against `public-status.v1.schema.json`; `grok_spec.py validate` returned `ok: true` with digest `bf6e7efcca675e8c37819ce0165eabbce741a3e4f0da9ccc2477cc4f895e80ad`.
- Static proof: focused Ruff and Bandit passed.

## Rulings

- Local PROJECT_STATE/receipt freshness and coherent public GitHub facts are independent axes: a stale claim makes overall status stale but does not erase an observed Check PASS/FAIL/PENDING or PR state.
- Failure projections are atomically persisted and retain the original successful observation epoch; repeated failures age the snapshot instead of letting `status` lie fresh.
- The GET budget is fixed at 16 to cover opening/closing reads, two compares and the bounded four-hop annotated-tag chain; no optional list or Check `details_url` is followed.
