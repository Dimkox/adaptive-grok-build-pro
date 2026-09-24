# Test plan — Consolidate repository-owned remaining issue fixes into one bounded batch from current main, preserve external blockers, run one final PR verification and prepare one successor PR

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Checked-in policy example cannot claim deployed authority | `tests.test_structure.StructureTests.test_trust_ci_policy_uses_immutable_sandbox_and_external_status` |
| P0 | Provider probes are marked attested/non-re-derivable | `tests.test_structure.StructureTests.test_l5_runtime_observation_marks_provider_probes_non_rederivable` |
| P1 | Existing Trust CI policy parser remains compatible | `trust-ci/tests/test_policy.py` |

## Automated checks

- Unit: `python3 -m unittest tests.test_structure`.
- Integration: Trust CI policy discovery with `PYTHONPATH=trust-ci/src:trust-ci/tests`.
- Contract: `python3 scripts/grok_verify.py --mode pr` and active change-spec validation.
- E2E: no provider/hosting E2E is authorized or required for this source-only slice.
- Static analysis: `python3 -m compileall -q scripts trust-ci/src` and `git diff --check`.

## Manual checks

- Confirm no provider, deployed Trust CI, key, database, or external hosting
  write occurred; confirm external blockers remain explicitly out of scope.
