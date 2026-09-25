# Test plan — Fix issue 227: inherited GIT_DIR or GIT_WORK_TREE can redirect repository identity and let a valid local grant authorize git push to a foreign pushurl. Add root-bound Git probes and explicit fail-closed denial. Never execute git push or access the network.

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Matching grant plus same-tree foreign checkout and foreign pushurl under inherited selectors is denied without executing push. | `tests.test_policy` |
| P0 | Root-bound Git probes ignore `GIT_DIR`/`GIT_WORK_TREE` for HEAD, dirty inventory and fingerprint. | `tests.test_util_fingerprint` |
| P1 | Hook subprocess preserves the fail-closed result and secret-safe reason. | `tests.test_hooks` |
| P1 | Clean-environment exact grant still allows only its named action. | Existing and new policy tests |

## Automated checks

- Unit: `python3 -m unittest tests.test_policy tests.test_util_fingerprint`
- Integration: `python3 -m unittest tests.test_hooks`
- Contract: `python3 -m unittest tests.test_structure tests.test_change_receipts`
- E2E: none; real push/network is forbidden.
- Static analysis: `git diff --check`; route-selected `grok_verify --mode pr`.

## Manual checks

- Inspect denial output for variable names and absence of foreign path/URL data.
- Confirm regression fixtures call only local Git setup/read commands and never
  invoke `git push`.
