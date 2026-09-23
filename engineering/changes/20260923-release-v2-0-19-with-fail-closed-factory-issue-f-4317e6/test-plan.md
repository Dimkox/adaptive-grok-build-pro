# Test plan — Release v2.0.19 with fail-closed factory issue fixes

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Later shell file has syntax error | `tests/test_verification_doctor.py` |
| P0 | Lint excludes scratch/generated/untracked paths and reports scope | `tests/test_verification_doctor.py` |
| P0 | Smoke observations are empty/pipeline/tool-discovery fail-closed | `trust-ci/tests/test_smoke.py` |
| P0 | Grant field migration preserves legacy reads and rejects ambiguity | `tests/test_policy.py` |
| P0 | Static landing focused mode accepts only the bounded safe topology | `tests/test_verification_doctor.py`, `tests/test_workflow_artifacts.py` |
| P1 | Full release verifier remains required for this mixed candidate | `scripts/grok_verify.py --mode pr` |

## Automated checks

- Unit: issue-specific Python and Trust CI smoke suites.
- Integration: combined verifier run over the exact release tree.
- Contract: change-spec/package and architecture checks.
- E2E: fake-runtime smoke script tests; no production endpoint writes.
- Static analysis: Ruff, Bandit, shell syntax, diff/secret checks.

## Manual checks

- Verify `VERSION`, README architecture links/current state, CHANGELOG and package indexes only
  after the fix tree is frozen.
- Verify no M8/DEV files or unrelated release-candidate content entered the tree.
