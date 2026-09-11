# Test plan — D5

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Missing/empty ledger count = 0 | new factory tests |
| P0 | Synthetic 30-row fixture does not count; activation false | new tests + existing `test_closed_m7_bundle_blocks_forged_thirty_row_qualification` stays green |
| P0 | append rejects synthetic and missing M7 flags; no row written | new tests |
| P0 | tuple mutation → new empty cohort | new tests |
| P0 | M9 qualification false: signed_input, environment, recovery, production, m8_not_activated | new delivery tests |
| P0 | deadline after 2026-09-08 does not waive | new tests |
| P1 | Unmodified `test_autonomy.py`, `test_m8_boundary.py`, `test_recovery.py`, controller tests still pass | existing |

No test may assert M8 `activated is True` or M9 operational `qualified is True`.

Automated: `python3 scripts/grok_verify.py --mode pr`.
