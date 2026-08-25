# Test plan

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Existing test_backup.py still green | unittest |
| P0 | test_m0_invariants: no PEM; Check Run id not UNKNOWN; local HMAC; webhook not done | unittest |
| P0 | If report cell is dated pass, assert that row contains a date and `pass` | new characterization |
| P0 | Live drill dump/verify/restore/restart | drill-report.md |
| P0 | Live volume not used as restore target | inspect throwaway mounts |

Automated: `python3 -m unittest trust-ci.tests.test_m0_invariants trust-ci.tests.test_backup` and `python3 scripts/grok_verify.py --mode pr`.
