# Test plan

| ID | Case | How |
| --- | --- | --- |
| P0 | Loopback live 200 | `curl -i http://127.0.0.1:18080/health/live` (host evidence) |
| P0 | Unsigned public ping 401 | curl Funnel URL; save status+snippet without secrets |
| P0 | Operator docs name Funnel webhook URL | `test_m0_invariants.py` after proof |
| P0 | M0.2 still not done / local HMAC | existing invariant |
| P1 | HMAC unit tests unchanged | `test_api.py` / `test_webhooks_github.py` |

No CI HTTP probe of Funnel. No signed public ping this slice.
