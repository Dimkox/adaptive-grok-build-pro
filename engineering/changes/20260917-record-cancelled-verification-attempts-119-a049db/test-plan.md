# Test plan — verification cancellation

| Priority | Scenario | Expected | Evidence |
| --- | --- | --- | --- |
| P0 | `_python` raises documented `SystemExit(143)` | Report and failed receipt with `outcome=cancelled`; CLI exits 143 and prints `CANCELLED` | verifier and CLI tests |
| P0 | Existing same-route verification receipt is pass before cancellation | Replaced with fail; status validation rejects prior pass as current | receipt integration test |
| P0 | `KeyboardInterrupt` at check dispatch | Explicit cancellation result persisted; CLI exits 130 and prints `CANCELLED` | verifier and CLI tests |
| P1 | Ordinary test failure | Existing failed result, not cancellation | regression control |
| P1 | Unexpected exception/SystemExit code | Not mislabeled cancelled or passed | exception control |
| P1 | Earlier check results exist before cancellation | Retained; later checks not dispatched | orchestration test |
| P1 | SIGKILL/host termination | No guarantee is claimed | documentation/contract review |

Run focused verification/receipt tests and cancellation reproduction, then `python3 scripts/grok_verify.py --mode pr`, then route-selected code/test reviews. Ensure every synthetic child process is terminated and reaped.
