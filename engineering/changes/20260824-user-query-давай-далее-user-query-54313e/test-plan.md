# Test plan — M0.3 bind main

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | GET protection binds epoch name + App ID 4694114 | Live GET 200; unittest pins payload + report cells |
| P0 | Same-text other actor does not satisfy | User status id `52802341946` success; PR #5 still `blocked`; App Check Run `97529209576` `action_required`; Checks POST 403 |
| P0 | Leftover Actions disabled | Catalog `340420982` `disabled_manually`; tree has no `.github/workflows/` |
| P0 | Bootstrap language superseded as current-state | README L11; new decisions entry; activation-report cells |
| P1 | M0.2 historical “Do not protect main” string remains | `test_m0_2_webhook_stage_closed_on_github_delivery` |
| P0 | PR #5 not merged | draft + `mergeable_state=blocked` |

## Automated checks

- Unit: `python3 -m unittest trust-ci.tests.test_m0_invariants`
- Static: `python3 scripts/grok_verify.py --mode pr`

## Manual checks

- Live GitHub GET/POST already executed this turn; unittests must not call GitHub or read keys.
