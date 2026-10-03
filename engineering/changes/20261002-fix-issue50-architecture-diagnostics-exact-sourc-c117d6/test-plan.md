# Test plan — Fix issue50 architecture diagnostics: exact source locations, malformed path and line-skip rejection, bounded architecture input preflight in verifier.

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Exact path coordinates, Unicode physical-line integrity, duplicate literal under actual failing rule | tests.test_architecture_model_preflight |
| P0 | Missing/schema/symlink/alias/syntax/duplicate/path/model bounds and blocked root discovery | tests.test_architecture_model_preflight |
| P1 | Valid loader/digest/view and doctor/verifier adoption compatibility | tests.test_architecture_model, tests.test_architecture_fitness, tests.test_verification_doctor |

## Automated checks

- RED: 14 new tests against the original candidate: 35 failures and one missing-doctor-item error, including an actual root-discovery marker written after malformed input.
- Additional RED: active-route refusal reached an invalid receipt rebind, missing receipt-disclosure metadata raised KeyError, and a nested same-key duplicate reported line 3 instead of independently expected line 6. All corrections have corresponding focused regressions.
- Final alias RED: a referenced contract hard-linked to the authority input was accepted because per-group inode maps were separate; the complete input-set map now has a direct regression.
- Focused GREEN: taskset -c 8,9 python3 -m unittest tests.test_architecture_model_preflight -q.
- Compatibility: taskset -c 8 python3 -m unittest tests.test_architecture_model tests.test_architecture_fitness -q and taskset -c 9 python3 -m unittest tests.test_verification_doctor -q; independent processes total two.
- Static: git diff --check and ruff on the four scoped product/test paths.
- Full PR verifier and selected independent review receipts belong to the controller on the integrated final candidate; focused results never substitute for them.
- Compatibility rerun: 86 doctor/verifier tests passed in 196.025 seconds after the loaded-input scope correction; intermediate failures were corrected rather than omitted from the evidence trail.

## Manual checks

- Inspect scoped diff for A/E boundary separation and unchanged version, state, generated architecture bytes and preserved dirty-tree inputs.
