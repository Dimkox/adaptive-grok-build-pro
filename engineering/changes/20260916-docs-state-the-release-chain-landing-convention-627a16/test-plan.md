# Test plan — release-chain convention and inspected causes

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | The three work_inventory causes equal what the retained job records say | `tests/test_project_state.py` exact-value pins for `retained_unresolved` and `superseded` |
| P0 | Published release records untouched | `tests/test_project_state.py` release assertions |
| P1 | START_HERE still carries its required sections after the added sentence | `tests/test_project_state.py` epoch/app consistency test |

## Automated checks

- `python3 -m unittest tests.test_project_state tests.test_structure` 
- `python3 scripts/grok_verify.py --mode pr`

## Manual checks

- Re-read each quoted cause against `trust_ci_jobs.result->commands` output tails for the named head.
- Confirm no tag or release moved: `git tag --list 'v2.0.1*'` and `gh release list` unchanged.
