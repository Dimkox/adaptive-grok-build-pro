# Test plan — v2.0.18 successor record

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | published_release binds v2.0.18 and prior holds v2.0.17 unchanged | `tests/test_project_state.py` |
| P0 | local_candidate published-form; successor-only identities; operational_activation false | `tests/test_project_state.py` |
| P0 | published ZIP+sidecar recomputed from tracked blobs equal the record | `tests/test_manifest_package.py` |
| P1 | current-state docs say v2.0.18 published; no activation claim | `tests/test_structure.py`, release review |

Commands: `python3 -m unittest tests.test_project_state tests.test_structure tests.test_manifest_package tests.test_change_spec` (119 OK), then `python3 scripts/grok_verify.py --mode pr`.
