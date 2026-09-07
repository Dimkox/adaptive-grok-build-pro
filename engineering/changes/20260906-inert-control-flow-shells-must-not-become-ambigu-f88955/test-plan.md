# Test plan — Inert control-flow shells must not become ambiguous-sensitive-shell or share one circuit-breaker objective

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Inert control-flow reads allow | `tests.test_hooks.HookPolicyTest.test_benign_shell_expansion_and_read_chain_remain_soft` |
| P0 | Unproven/sensitive forms still deny | existing deny methods in `tests.test_hooks` (unchanged) |
| P0 | Distinct catch-all objectives do not BLOCK | `tests.test_pre_tool_circuit_breaker` |
| P0 | Same catch-all shape BLOCKS; classified curl stays coarse | `tests.test_pre_tool_circuit_breaker` |

## Automated checks

- Unit: `python3 -m unittest tests.test_hooks tests.test_pre_tool_circuit_breaker tests.test_policy tests.test_protected_write_hook tests.test_policy_shell_targets -v`
- Integration: none
- Contract: schema 3 ledger fields unchanged; no `command` key; no raw argv
- E2E: none
- Static analysis: route `grok_verify --mode pr` if practical

## Manual checks

- None. Do not run factory-postgres-exit.
