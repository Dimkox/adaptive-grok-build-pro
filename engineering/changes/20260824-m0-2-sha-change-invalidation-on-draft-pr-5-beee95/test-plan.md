# Test plan

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Unit superseded-head already in MemoryStore tests | no product code change expected |
| P0 | `test_m0_invariants` still green (docs not retitled this slice) | unittest |
| P0 | Live: old SHA keeps 97390635614; new SHA different Check Run | `gh api` check-runs |
| P0 | HMAC 200, new job_id, secret not printed | container POST |

Automated: `python3 -m unittest trust-ci.tests.test_m0_invariants` and `python3 scripts/grok_verify.py --mode pr` after the pre-push commit.
