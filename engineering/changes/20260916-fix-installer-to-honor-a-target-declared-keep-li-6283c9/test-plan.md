# Test plan

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | KEEP reported; kept paths out of entries; absent/identical states | keep tests 1, 2, 4 |
| P0 | Drift conflict names the path, mutates nothing | keep test 3 |
| P0 | Closed record validation; symlinked record fails; no-record parity | keep tests 5–7 + 17 inherited arms |

Commands: `python3 -m unittest tests.test_installer` (24 OK), then `python3 scripts/grok_verify.py --mode pr`.
