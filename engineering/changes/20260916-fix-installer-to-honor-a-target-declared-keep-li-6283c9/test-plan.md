# Test plan

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | KEEP reported; kept paths out of entries; absent/identical states; target_state stays directory | keep tests 1-4 + target-state asserts |
| P0 | Drift conflict names the path, mutates nothing | keep test 3 |
| P0 | Closed record validation; symlinked record/kept path and FIFO fail closed; oversized record refused; target-owned/unmanaged and nested identical/drift states; no-record parity frozen by 346-entry manifest digest | keep arms incl. review-round additions + 17 inherited |

Commands: `python3 -m unittest tests.test_installer` (24 OK), then `python3 scripts/grok_verify.py --mode pr`.
